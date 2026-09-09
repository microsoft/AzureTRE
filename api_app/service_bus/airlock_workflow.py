import asyncio
import json

from azure.servicebus.aio import AutoLockRenewer, ServiceBusClient
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from pydantic import ValidationError

from core import config, credentials
from db.repositories.airlock_requests import AirlockRequestRepository
from db.repositories.operations import OperationRepository
from db.repositories.resource_templates import ResourceTemplateRepository
from db.repositories.resources_history import ResourceHistoryRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.workspaces import WorkspaceRepository
from db.errors import EntityDoesNotExist
from db.repositories.operations import WORKSPACE_LEASE_EXPIRY_SECONDS
from models.domain.authentication import User
from models.domain.airlock_request import AirlockReviewUserResource
from models.domain.resource import ResourceType
from services.airlock import _deploy_vm, wait_for_successful_operation, update_and_publish_event_airlock_request, disable_user_resource
from api.routes.resource_helpers import send_uninstall_message
from services.logging import logger


class AirlockWorkflowUpdater:
    async def init_repos(self):
        self.airlock_request_repo = await AirlockRequestRepository.create()
        self.operations_repo = await OperationRepository.create()
        self.resource_template_repo = await ResourceTemplateRepository.create()
        self.resource_history_repo = await ResourceHistoryRepository.create()
        self.user_resource_repo = await UserResourceRepository.create()
        self.workspace_service_repo = await WorkspaceServiceRepository.create()
        self.workspace_repo = await WorkspaceRepository.create()

    async def receive_messages(self):
        while True:
            try:
                async with credentials.get_credential_async_context() as credential:
                    async with ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential) as client:
                        receiver = client.get_queue_receiver(queue_name=config.SERVICE_BUS_AIRLOCK_WORKFLOW_QUEUE)
                        async with receiver:
                            messages = await receiver.receive_messages(max_message_count=1, max_wait_time=1)
                            for message in messages:
                                async with AutoLockRenewer() as renewer:
                                    renewer.register(
                                        receiver,
                                        message,
                                        max_lock_renewal_duration=2 * WORKSPACE_LEASE_EXPIRY_SECONDS)
                                    if await self.process_message(message):
                                        await receiver.complete_message(message)
                                    else:
                                        await receiver.abandon_message(message)
            except OperationTimeoutError:
                logger.debug("No Airlock workflow messages available")
            except ServiceBusConnectionError:
                logger.warning("Airlock workflow Service Bus connection failed; retrying")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Airlock workflow receiver failed; retrying")
            await asyncio.sleep(10)

    async def process_message(self, message) -> bool:
        try:
            payload = json.loads(str(message))
            user = User.model_validate(payload["user"])
            try:
                user_resource = await self.user_resource_repo.get_user_resource_by_id(
                    workspace_id=payload["review_workspace_id"],
                    service_id=payload["review_workspace_service_id"],
                    resource_id=payload["user_resource_id"])
            except EntityDoesNotExist:
                if payload["workflow"] == "cleanup":
                    logger.info("Airlock review resource %s is already deleted", payload["user_resource_id"])
                    return True
                user_resource = None
            if payload["workflow"] == "cleanup":
                workspace_service = await self.workspace_service_repo.get_workspace_service_by_id(
                    workspace_id=payload["review_workspace_id"],
                    service_id=payload["review_workspace_service_id"])
                if user_resource is None:
                    return True
                disable_operation = await disable_user_resource(
                    user_resource, user, workspace_service, self.user_resource_repo,
                    self.resource_template_repo, self.operations_repo, self.resource_history_repo)
                await wait_for_successful_operation(self.operations_repo, disable_operation.id)
            else:
                await wait_for_successful_operation(self.operations_repo, payload["operation_id"])
            if user_resource is not None and not payload.get("uninstall_started", False):
                delete_operation = await send_uninstall_message(
                    resource=user_resource,
                    resource_repo=self.user_resource_repo,
                    operations_repo=self.operations_repo,
                    resource_type=ResourceType.UserResource,
                    resource_template_repo=self.resource_template_repo,
                    resource_history_repo=self.resource_history_repo,
                    user=user)
                await wait_for_successful_operation(self.operations_repo, delete_operation.id)

            if payload["workflow"] == "redeploy":
                airlock_request = await self.airlock_request_repo.get_airlock_request_by_id(payload["airlock_request_id"])
                workspace = await self.workspace_repo.get_workspace_by_id(payload["workspace_id"])
                user_resource, _ = await _deploy_vm(
                    airlock_request, user, workspace,
                    payload["review_workspace_id"], payload["review_workspace_service_id"],
                    payload["user_resource_template_name"], self.user_resource_repo,
                    self.workspace_service_repo, self.operations_repo,
                    self.resource_template_repo, self.resource_history_repo)
                await update_and_publish_event_airlock_request(
                    airlock_request, self.airlock_request_repo, user, workspace,
                    review_user_resource=AirlockReviewUserResource(
                        workspaceId=payload["review_workspace_id"],
                        workspaceServiceId=payload["review_workspace_service_id"],
                        userResourceId=user_resource.id))
            return True
        except (json.JSONDecodeError, KeyError, ValidationError):
            logger.exception("Invalid Airlock workflow message")
            return True
        except Exception:
            logger.exception("Airlock workflow message failed; it will be retried")
            return False
