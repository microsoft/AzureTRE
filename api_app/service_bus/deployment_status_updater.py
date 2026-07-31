import asyncio
import json
import uuid
import time

from pydantic import ValidationError, parse_obj_as

from api.routes.resource_helpers import get_timestamp
from models.domain.resource import Output, ResourceType
from db.repositories.resources_history import ResourceHistoryRepository
from models.domain.request_action import RequestAction
from db.repositories.resource_templates import ResourceTemplateRepository
from service_bus.helpers import send_deployment_message, update_resource_for_step
from azure.servicebus import NEXT_AVAILABLE_SESSION
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from db.repositories.operations import OperationRepository
from core import config, credentials
from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.operation import DeploymentStatusUpdateMessage, Operation, OperationStep, Status
from resources import strings
from services.logging import logger, tracer
from db.repositories.workspaces import WorkspaceRepository
from models.schemas.resource import ResourcePatch
from azure.cosmos.exceptions import CosmosAccessConditionFailedError


MAX_CLEANUP_RETRIES = 3


class DeploymentStatusUpdater():
    def __init__(self):
        pass

    async def init_repos(self):
        self.operations_repo = await OperationRepository.create()
        self.resource_repo = await ResourceRepository.create()
        self.resource_template_repo = await ResourceTemplateRepository.create()
        self.resource_history_repo = await ResourceHistoryRepository.create()

    def run(self, *args, **kwargs):
        asyncio.run(self.receive_messages())

    async def receive_messages(self):
        with tracer.start_as_current_span("deployment_status_receive_messages"):
            last_heartbeat_time = 0
            polling_count = 0
            while True:
                complete_message = True
                async with credentials.get_credential_async_context() as credential:
                    async with ServiceBusClient(fully_qualified_namespace=config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential=credential) as service_bus_client:
                        try:
                            logger.debug("Creating Deployment Status receiver session")
                            async with service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE, max_wait_time=config.SERVICE_BUS_MAX_WAIT_TIME, session_id=NEXT_AVAILABLE_SESSION) as receiver:
                                async with AutoLockRenewer() as renewer:
                                    renewer.register(receiver, receiver.session, max_lock_renewal_duration=60)

                                    async for msg in receiver:
                                        complete_message = await self.process_message(msg)
                                        if complete_message:
                                            await receiver.complete_message(msg)
                                        else:
                                            await receiver.abandon_message(msg)

                                polling_count = 0

                        except OperationTimeoutError:
                            polling_count += 1
                            # log a heartbeat every ~5 minutes when queue is idle (max_wait_time is usually ~10s)
                            if time.time() - last_heartbeat_time > 300:
                                logger.info(f"Deployment status updater polling... (idle checks: {polling_count})")
                                last_heartbeat_time = time.time()
                        except ServiceBusConnectionError as e:
                            logger.warning(f"Service Bus connection error in deployment status updater, will retry: {e}")
                            await asyncio.sleep(5)
                        except Exception:
                            logger.exception("Unexpected error in deployment status receiver loop")
                            await asyncio.sleep(5)

    async def process_message(self, msg) -> bool:
        complete_message = False
        with tracer.start_as_current_span("process_message") as current_span:
            try:
                message = parse_obj_as(DeploymentStatusUpdateMessage, json.loads(str(msg)))

                current_span.set_attribute("step_id", message.stepId)
                current_span.set_attribute("operation_id", message.operationId)
                current_span.set_attribute("status", message.status)

                complete_message = await self.update_status_in_database(message)
                logger.info(f"Update status in DB for {message.operationId} - {message.status}")
            except (json.JSONDecodeError, ValidationError):
                logger.exception(f"{strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT}: {msg.correlation_id}")
            except Exception:
                logger.exception(f"Exception processing message: {msg.correlation_id}")

        return complete_message

    async def update_status_in_database(self, message: DeploymentStatusUpdateMessage):
        """
        Get the operation the message references, and find the step within the operation that is to be updated
        Update the status of the step. If it's a single step operation, copy the status into the operation status. If it's a multi step,
        update the step and set the overall status to "pipeline_deploying".
        If there is another step in the operation after this one, process the substitutions + patch, then enqueue a message to process it.
        """
        result = False

        try:
            # update the op
            operation = await self.operations_repo.get_operation_by_id(str(message.operationId))
            step_to_update = None
            is_last_step = False

            current_step_index = 0
            for i, step in enumerate(operation.steps):
                # TODO more simple condition
                if step.id == message.stepId and step.resourceId == str(message.id):
                    step_to_update = step
                    current_step_index = i
                    if i == (len(operation.steps) - 1):
                        is_last_step = True

            if step_to_update is None:
                raise f"Error finding step {message.stepId} in operation {message.operationId}"

            # update the step status
            step_to_update.status = message.status
            step_to_update.message = message.message
            step_to_update.updatedWhen = get_timestamp()

            # update the overall headline operation status
            await self.update_overall_operation_status(operation, step_to_update, is_last_step)

            # save the operation
            await self.operations_repo.update_item(operation)

            # copy the step status to the resource item, for convenience
            resource_id = uuid.UUID(step_to_update.resourceId)

            resource = await self.resource_repo.get_resource_by_id(resource_id)
            resource.deploymentStatus = step_to_update.status
            await self.resource_repo.update_item(resource)

            # if the step failed, or this queue message is an intermediary ("now deploying..."), return here.
            if not step_to_update.is_success():
                return True

            # update the resource doc to persist any outputs
            resource = await self.resource_repo.get_resource_dict_by_id(resource_id)
            resource_to_persist = self.create_updated_resource_document(resource, message)
            await self.resource_repo.update_item_dict(resource_to_persist)

            # If the 'main' step succeeded for an uninstall operation, free any allocated address space
            # owned by a WorkspaceService resource. MUST be executed BEFORE preparing/enqueuing any next step
            # (such as a trailing workspace upgrade step), so Cosmos DB state is updated before the next step
            # queries the workspace document.
            if step_to_update.templateStepId == "main" and step_to_update.is_success() and operation.action == RequestAction.UnInstall:
                await self._free_workspace_address_space(resource_to_persist, operation)

            # more steps in the op to do?
            if is_last_step is False:
                assert current_step_index < (len(operation.steps) - 1)
                next_step = operation.steps[current_step_index + 1]

                # catch any errors in updating the resource - maybe Cosmos / schema invalid etc, and report them back to the op
                try:
                    # parent resource is always retrieved via cosmos, hence it is always with redacted sensitive values
                    parent_resource = await self.resource_repo.get_resource_by_id(next_step.sourceTemplateResourceId)
                    resource_to_send = await update_resource_for_step(
                        operation_step=next_step,
                        resource_repo=self.resource_repo,
                        resource_template_repo=self.resource_template_repo,
                        resource_history_repo=self.resource_history_repo,
                        root_resource=None,
                        step_resource=parent_resource,
                        resource_to_update_id=next_step.resourceId,
                        primary_action=operation.action,
                        user=operation.user)

                    # create + send the message
                    logger.info(f"Sending next step in operation to deployment queue -> step_id: {next_step.templateStepId}, action: {next_step.resourceAction}")
                    content = json.dumps(resource_to_send.get_resource_request_message_payload(operation_id=operation.id, step_id=next_step.id, action=next_step.resourceAction))
                    await send_deployment_message(content=content, correlation_id=operation.id, session_id=resource_to_send.id, action=next_step.resourceAction)
                except Exception as e:
                    logger.exception("Unable to send update for resource in pipeline step")
                    next_step.message = repr(e)
                    next_step.status = Status.UpdatingFailed
                    await self.update_overall_operation_status(operation, next_step, is_last_step)
                    await self.operations_repo.update_item(operation)

            result = True

        except EntityDoesNotExist:
            # Marking as true as this message will never succeed anyways and should be removed from the queue.
            result = True
            logger.exception(strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(message.id))
        except Exception:
            logger.exception("Failed to update status")

        return result

    async def _free_workspace_address_space(self, resource_to_persist: dict, operation: Operation):
        """
        Frees any allocated address space owned by a WorkspaceService resource after a successful uninstall main step.
        Updates the parent Workspace document in Cosmos DB so that subsequent pipeline steps (e.g., workspace upgrade)
        or future operations rely on the updated address_spaces property.
        """
        if resource_to_persist.get("resourceType") != ResourceType.WorkspaceService:
            return

        address_to_free = resource_to_persist.get("properties", {}).get("address_space")
        parent_workspace_id = resource_to_persist.get("workspaceId")
        resource_id = resource_to_persist.get("id")

        if not address_to_free or not parent_workspace_id:
            return

        try:
            workspace_repo = await WorkspaceRepository.create()
            for attempt in range(MAX_CLEANUP_RETRIES):
                try:
                    workspace = await workspace_repo.get_workspace_by_id(parent_workspace_id)
                    workspace_address_spaces = workspace.properties.get("address_spaces", [])
                    if address_to_free not in workspace_address_spaces:
                        break
                    new_address_spaces = [a for a in workspace_address_spaces if a != address_to_free]
                    workspace_patch = ResourcePatch()
                    workspace_patch.properties = {"address_spaces": new_address_spaces}

                    # Note: patch_workspace with force_version_update=False updates the Cosmos DB record only;
                    # it does not trigger an independent deployment operation. Infrastructure updates (Terraform)
                    # are driven by the trailing workspace upgrade step in the uninstall pipeline.
                    await workspace_repo.patch_workspace(
                        workspace,
                        workspace_patch,
                        workspace.etag,
                        self.resource_template_repo,
                        self.resource_history_repo,
                        operation.user,
                        False
                    )
                    logger.info(f"Freed address space {address_to_free} from workspace {parent_workspace_id} after successful uninstall of {resource_id}")
                    break
                except CosmosAccessConditionFailedError:
                    if attempt == MAX_CLEANUP_RETRIES - 1:
                        raise
                    logger.warning(f"ETag conflict when freeing workspace address space after successful uninstall. Retrying (attempt {attempt + 1}/{MAX_CLEANUP_RETRIES})...")
        except Exception as e:
            logger.error(f"[ADDRESS_SPACE_CLEANUP_FAILED] Failed to free workspace address space {address_to_free} for workspace {parent_workspace_id} after uninstalling {resource_id}: {e}", exc_info=True)

    async def update_overall_operation_status(self, operation: Operation, step: OperationStep, is_last_step: bool):
        operation.updatedWhen = get_timestamp()

        # if it's a one step operation, just replicate the status
        if len(operation.steps) == 1:
            operation.status = step.status
            operation.message = step.message
            return

        operation.status = Status.PipelineRunning
        operation.message = "Multi step pipeline running. See steps for details."

        if step.is_failure():
            operation.status = self.get_failure_status_for_action(operation.action)
            operation.message = f"Multi step pipeline failed on step {step.templateStepId}"

            # pipeline failed - update the primary resource (from the main step) as failed too
            main_step = None
            for i, step in enumerate(operation.steps):
                if step.templateStepId == "main":
                    main_step = step
                    break

            if main_step:
                primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                primary_resource.deploymentStatus = operation.status
                await self.resource_repo.update_item(primary_resource)

        if step.is_success() and is_last_step:
            operation.status = self.get_success_status_for_action(operation.action)
            operation.message = "Multi step pipeline completed successfully"

    def get_success_status_for_action(self, action: RequestAction):
        status = Status.ActionSucceeded

        if action == RequestAction.Install:
            status = Status.Deployed
        elif action == RequestAction.UnInstall:
            status = Status.Deleted
        elif action == RequestAction.Upgrade:
            status = Status.Updated

        return status

    def get_failure_status_for_action(self, action: RequestAction):
        status = Status.ActionFailed

        if action == RequestAction.Install:
            status = Status.DeploymentFailed
        elif action == RequestAction.UnInstall:
            status = Status.DeletingFailed
        elif action == RequestAction.Upgrade:
            status = Status.UpdatingFailed

        return status

    def create_updated_resource_document(self, resource: dict, message: DeploymentStatusUpdateMessage):
        """
        Merge the outputs with the resource document to persist
        """

        # although outputs are likely to be relevant when resources are moving to "deployed" status,
        # lets not limit when we update them and have the resource process make that decision.
        # need to convert porter outputs to dict so boolean values are converted to bools, not strings
        output_dict = self.convert_outputs_to_dict(message.outputs)
        resource["properties"].update(output_dict)

        return resource

    def convert_outputs_to_dict(self, outputs_list: [Output]):
        """
        Convert a list of Porter outputs to a dictionary
        """

        result_dict = {}
        for msg in outputs_list:
            if msg.Value is None:
                continue
            name = msg.Name
            value = msg.Value
            obj_type = msg.Type

            #
            if obj_type == 'string' and isinstance(value, str):
                value = value.strip("'").strip('"')
            elif obj_type == 'boolean':
                if isinstance(value, str):
                    value = value.strip("'").strip('"')
                value = (value.lower() == 'true')

            result_dict[name] = value

        return result_dict
