import asyncio
import copy
import json
import uuid
import time
from typing import Optional, Tuple

from pydantic import ValidationError, TypeAdapter

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
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.schemas.resource import ResourcePatch
from azure.cosmos.exceptions import CosmosAccessConditionFailedError


MAX_CLEANUP_RETRIES = 3
MAX_CLEANUP_DELIVERY_COUNT = 10
# Azure Service Bus default max delivery count is 10.
# ServiceBusReceivedMessage.delivery_count is 1-based in Azure Service Bus:
# attempt 1 has delivery_count = 1, and attempt 10 (the final processable attempt before DLQ) has delivery_count = 10.
# When delivery_count >= MAX_CLEANUP_DELIVERY_COUNT, this is the final delivery attempt before Service Bus dead-letters the message.
FINAL_CLEANUP_DELIVERY_COUNT = MAX_CLEANUP_DELIVERY_COUNT


class AddressSpaceConflictError(Exception):
    """Raised when address space cleanup encounters a terminal conflict with another active service."""
    pass


class DeploymentStatusUpdater():
    def __init__(self):
        pass

    async def init_repos(self):
        self.operations_repo = await OperationRepository.create()
        self.resource_repo = await ResourceRepository.create()
        self.workspace_repo = await WorkspaceRepository.create()
        self.workspace_services_repo = await WorkspaceServiceRepository.create()
        self.resource_template_repo = await ResourceTemplateRepository.create()
        self.resource_history_repo = await ResourceHistoryRepository.create()

    def run(self, *args, **kwargs):
        asyncio.run(self.receive_messages())

    async def receive_messages(self):
        with tracer.start_as_current_span("deployment_status_receive_messages"):
            last_heartbeat_time = 0
            polling_count = 0

            while True:
                try:
                    current_time = time.time()
                    polling_count += 1
                    # Log a heartbeat message every 60 seconds to show the service is still working
                    if current_time - last_heartbeat_time >= 60:
                        logger.info(f"Queue reader heartbeat: Polled {config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE} queue {polling_count} times in the last minute")
                        last_heartbeat_time = current_time
                        polling_count = 0

                    async with credentials.get_credential_async_context() as credential:
                        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

                        logger.debug(f"Looking for new messages on {config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE} queue...")
                        # max_wait_time=1 -> don't hold the session open after processing of the message has finished
                        async with service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE, max_wait_time=1, session_id=NEXT_AVAILABLE_SESSION) as receiver:
                            logger.info(f"Got a session containing messages: {receiver.session.session_id}")
                            async with AutoLockRenewer() as renewer:
                                renewer.register(receiver, receiver.session, max_lock_renewal_duration=60)
                                async for msg in receiver:
                                    complete_message = await self.process_message(msg)
                                    if complete_message:
                                        await receiver.complete_message(msg)
                                    else:
                                        # could have been any kind of transient issue, we'll abandon back to the queue, and retry
                                        await receiver.abandon_message(msg)
                            logger.info(f"Closing session: {receiver.session.session_id}")

                except OperationTimeoutError:
                    # Timeout occurred whilst connecting to a session - this is expected and indicates no non-empty sessions are available
                    logger.debug("No sessions for this process. Will look again...")

                except ServiceBusConnectionError:
                    # Occasionally there will be a transient / network-level error in connecting to SB.
                    logger.info("Unknown Service Bus connection error. Will retry...")

                except Exception as e:
                    # Catch all other exceptions, log them via .exception to get the stack trace, and reconnect
                    logger.exception(f"Unknown exception. Will retry - {e}")

    async def process_message(self, msg) -> bool:
        complete_message = False
        with tracer.start_as_current_span("process_message") as current_span:
            try:
                message = TypeAdapter(DeploymentStatusUpdateMessage).validate_python(json.loads(str(msg)))

                current_span.set_attribute("step_id", str(message.stepId))
                current_span.set_attribute("operation_id", str(message.operationId))
                current_span.set_attribute("status", str(message.status))

                raw_delivery_count = getattr(msg, "delivery_count", 0)
                delivery_count = raw_delivery_count if raw_delivery_count is not None else 0
                is_final_delivery = delivery_count >= FINAL_CLEANUP_DELIVERY_COUNT

                complete_message = await self.update_status_in_database(message, is_final_delivery=is_final_delivery)
                logger.info(f"Update status in DB for {message.operationId} - {message.status}")
            except (json.JSONDecodeError, ValidationError):
                logger.exception(f"{strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT}: {msg.correlation_id}")
            except Exception:
                logger.exception(f"Exception processing message: {msg.correlation_id}")

        return complete_message

    async def update_status_in_database(self, message: DeploymentStatusUpdateMessage, is_final_delivery: bool = False):
        """
        Get the operation the message references, and find the step within the operation that is to be updated
        Update the status of the step. If it's a single step operation, copy the status into the operation status. If it's a multi step,
        update the step and set the overall status to "pipeline_deploying".
        If there is another step in the operation after this one, process the substitutions + patch, then enqueue a message to process it.
        """
        result = False
        operation = None
        step_to_update = None

        try:
            # update the op
            operation = await self.operations_repo.get_operation_by_id(str(message.operationId))
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
                raise Exception(f"Error finding step {message.stepId} in operation {message.operationId}")

            # If address space cleanup for this uninstall operation is already in a terminal state (completed or failed),
            # the entire operation is already finalized. Ignore any delayed or duplicate messages for ANY step in this
            # operation to prevent overwriting resources with stale status or reopening the operation.
            if (
                operation.action == RequestAction.UnInstall
                and self._is_cleanup_terminal(operation)
            ):
                logger.info(
                    f"Message {message.stepId} (step {step_to_update.templateStepId}, status {message.status}) received for operation {operation.id}, "
                    f"but uninstall cleanup is already terminal ({operation.status}). Ignoring to prevent stale writes."
                )
                return True

            # update the step status
            step_to_update.status = message.status
            step_to_update.message = message.message
            step_to_update.updatedWhen = get_timestamp()

            resource_id = uuid.UUID(step_to_update.resourceId)

            # If this is the main step of an uninstall succeeding for a workspace service with an address space,
            # ensure the trailing workspace upgrade fallback step is appended BEFORE calculating
            # and persisting the main step's overall status. This ensures is_last_step is False
            # and the operation is persisted as PipelineRunning continuously in Cosmos DB, eliminating any
            # window where resource_has_active_operation sees the operation as Deleted.
            if (
                step_to_update.templateStepId == "main"
                and step_to_update.resourceId == operation.resourceId
                and step_to_update.is_success()
                and operation.action == RequestAction.UnInstall
                and not self._has_workspace_upgrade_step(operation, current_step_index)
            ):
                resource_dict = await self.resource_repo.get_resource_dict_by_id(resource_id)
                if self._is_workspace_service_with_address_space(resource_dict):
                    operation.steps.append(self._create_workspace_upgrade_step(resource_dict))
                    is_last_step = False

            # Is this the address space cleanup step?
            is_cleanup_step = (
                step_to_update.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID
                and step_to_update.resourceType in (ResourceType.Workspace, ResourceType.Workspace.value)
                and step_to_update.resourceAction == RequestAction.Upgrade
                and operation.action == RequestAction.UnInstall
                and is_last_step
            )

            # For the address space cleanup step, we MUST run cleanup before persisting the
            # final successful operation status. This keeps the operation active in Cosmos DB
            # (so resource_has_active_operation blocks new allocations and workspace updates)
            # until the cleanup has been durably committed.
            if is_cleanup_step and step_to_update.is_success():
                try:
                    freed = await self._free_workspace_address_space(operation)
                except AddressSpaceConflictError as e:
                    logger.error(f"[ADDRESS_SPACE_CONFLICT] {e}")
                    step_to_update.status = Status.UpdatingFailed
                    step_to_update.message = f"Terminal address space conflict: {e}"
                    resource_to_update = await self.resource_repo.get_resource_by_id(resource_id)
                    resource_to_update.deploymentStatus = step_to_update.status
                    await self.resource_repo.update_item(resource_to_update)
                    main_step = next(
                        (op_step for op_step in operation.steps
                         if op_step.templateStepId == "main"
                         and op_step.resourceId == operation.resourceId),
                        None
                    )
                    if main_step:
                        primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                        primary_resource.deploymentStatus = Status.DeletingFailed
                        await self.resource_repo.update_item(primary_resource)
                    await self.update_overall_operation_status(operation, step_to_update, is_last_step)
                    await self.operations_repo.update_item(operation)
                    return True
                except Exception as e:
                    logger.error(f"[ADDRESS_SPACE_CLEANUP_FAILED] Unexpected error freeing workspace address space: {e}", exc_info=True)
                    freed = False

                if not freed:
                    if is_final_delivery:
                        cleanup_failure_message = f"Address space cleanup failed after {MAX_CLEANUP_DELIVERY_COUNT} delivery attempts. Marking operation as failed to unblock workspace."
                        logger.error(f"[ADDRESS_SPACE_CLEANUP_MAX_DELIVERIES] {cleanup_failure_message}")
                        step_to_update.status = Status.UpdatingFailed
                        step_to_update.message = cleanup_failure_message
                        resource_to_update = await self.resource_repo.get_resource_by_id(resource_id)
                        resource_to_update.deploymentStatus = step_to_update.status
                        await self.resource_repo.update_item(resource_to_update)
                        main_step = next(
                            (op_step for op_step in operation.steps
                             if op_step.templateStepId == "main"
                             and op_step.resourceId == operation.resourceId),
                            None
                        )
                        if main_step:
                            primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                            primary_resource.deploymentStatus = Status.DeletingFailed
                            await self.resource_repo.update_item(primary_resource)
                        await self.update_overall_operation_status(operation, step_to_update, is_last_step)
                        await self.operations_repo.update_item(operation)
                        return True
                    else:
                        cleanup_failure_message = "Address space cleanup failed after maximum retries; the message will be retried."
                        step_to_update.status = Status.Updating
                        step_to_update.message = cleanup_failure_message
                        resource_to_update = await self.resource_repo.get_resource_by_id(resource_id)
                        resource_to_update.deploymentStatus = step_to_update.status
                        await self.resource_repo.update_item(resource_to_update)
                        operation.status = Status.PipelineRunning
                        await self.operations_repo.update_item(operation)
                        return False
                else:
                    step_to_update.message = strings.ADDRESS_SPACE_CLEANUP_SUCCESS

            try:
                # copy the step status to the resource item, for convenience
                resource = await self.resource_repo.get_resource_by_id(resource_id)
                resource.deploymentStatus = step_to_update.status
                await self.resource_repo.update_item(resource)

                # if the step failed, or this queue message is an intermediary ("now deploying..."), return here.
                if not step_to_update.is_success():
                    await self.update_overall_operation_status(operation, step_to_update, is_last_step)
                    await self.operations_repo.update_item(operation)
                    return True

                # update the resource doc to persist any outputs
                resource = await self.resource_repo.get_resource_dict_by_id(resource_id)
                resource_to_persist = self.create_updated_resource_document(resource, message)
                await self.resource_repo.update_item_dict(resource_to_persist)

                if is_cleanup_step and step_to_update.is_success():
                    # Restore the primary resource to Deleted when cleanup succeeds
                    main_step = next(
                        (op_step for op_step in operation.steps
                         if op_step.templateStepId == "main"
                         and op_step.resourceId == operation.resourceId),
                        None
                    )
                    if main_step:
                        primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                        if primary_resource.deploymentStatus != Status.Deleted:
                            primary_resource.deploymentStatus = Status.Deleted
                            await self.resource_repo.update_item(primary_resource)

                # update the overall headline operation status
                await self.update_overall_operation_status(operation, step_to_update, is_last_step)

                # save the operation with final status LAST, after all resource updates are committed
                for attempt in range(MAX_CLEANUP_RETRIES):
                    try:
                        await self.operations_repo.update_item(operation)
                        break
                    except CosmosAccessConditionFailedError:
                        if attempt == MAX_CLEANUP_RETRIES - 1:
                            raise
                        logger.warning(f"ETag conflict when saving operation {operation.id}. Retrying (attempt {attempt + 1}/{MAX_CLEANUP_RETRIES})...")
                        fresh_op = await self.operations_repo.get_operation_by_id(operation.id)
                        step_to_update, is_last_step, current_step_index = self._merge_operation_steps(
                            in_memory_op=operation,
                            fresh_op=fresh_op,
                            step_id_to_update=step_to_update.id,
                            step_status=step_to_update.status,
                            step_message=step_to_update.message,
                        )
                        await self.update_overall_operation_status(fresh_op, step_to_update, is_last_step)
                        operation = fresh_op
            except Exception as e:
                if is_cleanup_step and step_to_update.is_success():
                    logger.error(f"[CLEANUP_FINALIZATION_FAILED] Error in post-cleanup writes: {e}", exc_info=True)
                    if is_final_delivery:
                        # Final delivery handling: must retry and verify all required resource and operation writes
                        workspace_persisted = False
                        try:
                            resource = await self.resource_repo.get_resource_by_id(resource_id)
                            resource.deploymentStatus = step_to_update.status
                            await self.resource_repo.update_item(resource)
                            resource_dict = await self.resource_repo.get_resource_dict_by_id(resource_id)
                            resource_to_persist = self.create_updated_resource_document(resource_dict, message)
                            await self.resource_repo.update_item_dict(resource_to_persist)
                            workspace_persisted = True
                        except Exception as ws_err:
                            logger.error(f"Failed to persist workspace resource status/outputs on final delivery: {ws_err}", exc_info=True)

                        primary_persisted = False
                        main_step = next(
                            (op_step for op_step in operation.steps
                             if op_step.templateStepId == "main"
                             and op_step.resourceId == operation.resourceId),
                            None
                        )
                        if main_step:
                            try:
                                primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                                if primary_resource.deploymentStatus != Status.Deleted:
                                    primary_resource.deploymentStatus = Status.Deleted
                                    await self.resource_repo.update_item(primary_resource)
                                primary_persisted = True
                            except Exception as prim_err:
                                logger.error(f"Failed to restore primary resource to Deleted on final delivery: {prim_err}", exc_info=True)
                        else:
                            primary_persisted = True

                        operation_persisted = False
                        if workspace_persisted and primary_persisted:
                            try:
                                fresh_op = await self.operations_repo.get_operation_by_id(str(message.operationId))
                                fresh_step, fresh_is_last, _ = self._merge_operation_steps(
                                    in_memory_op=operation,
                                    fresh_op=fresh_op,
                                    step_id_to_update=step_to_update.id,
                                    step_status=step_to_update.status,
                                    step_message=strings.ADDRESS_SPACE_CLEANUP_SUCCESS,
                                )
                                await self.update_overall_operation_status(fresh_op, fresh_step, fresh_is_last)
                                await self.operations_repo.update_item(fresh_op)
                                operation_persisted = True
                            except Exception as op_err:
                                logger.error(f"Failed to persist terminal operation status on final delivery: {op_err}", exc_info=True)

                        if workspace_persisted and primary_persisted and operation_persisted:
                            logger.info(f"All required resource and operation writes successfully persisted on final delivery for operation {operation.id}. Completing message.")
                            return True
                        else:
                            logger.error(
                                f"[CLEANUP_FINALIZATION_DEAD_LETTER] Could not persist all required states for "
                                f"operation {operation.id} on final delivery {MAX_CLEANUP_DELIVERY_COUNT} "
                                f"(workspace={workspace_persisted}, primary={primary_persisted}, op={operation_persisted}). "
                                f"Returning False so message is dead-lettered for manual recovery."
                            )
                            return False
                    else:
                        return False
                else:
                    raise

            # more steps in the op to do?
            if is_last_step is False:
                assert current_step_index < (len(operation.steps) - 1)
                next_step = operation.steps[current_step_index + 1]

                # catch any errors in updating the resource - maybe Cosmos / schema invalid etc, and report them back to the op
                try:
                    # parent resource is always retrieved via cosmos, hence it is always with redacted sensitive values
                    if next_step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID:
                        if (
                            self._is_cleanup_terminal(operation)
                            or next_step.message == strings.ADDRESS_SPACE_CLEANUP_SUCCESS
                            or next_step.is_failure()
                            or next_step.status in (Status.Updating, Status.UpdatingFailed)
                        ):
                            logger.info(
                                f"Address space cleanup step {next_step.id} in operation {operation.id} "
                                f"is already completed or in progress. Skipping enqueue."
                            )
                            return True

                        workspace = await self.workspace_repo.get_workspace_by_id(next_step.resourceId)
                        resource_to_send = copy.deepcopy(workspace)
                        cleanup_details = await self._get_address_cleanup_details(operation)
                        if cleanup_details:
                            address_to_free, parent_workspace_id, service_resource_id, _ = cleanup_details
                            # Validate active-service ownership before enqueueing this upgrade
                            workspace_services_repo = getattr(self, "workspace_services_repo", None)
                            if workspace_services_repo is None:
                                from db.repositories.workspace_services import WorkspaceServiceRepository
                                workspace_services_repo = await WorkspaceServiceRepository.create()

                            active_services = await workspace_services_repo.get_active_workspace_services_for_workspace(parent_workspace_id)
                            conflicting_services = [s for s in active_services if s.id != service_resource_id and s.properties.get("address_space") == address_to_free]
                            if conflicting_services:
                                raise AddressSpaceConflictError(
                                    f"Address space {address_to_free} is allocated to active service {conflicting_services[0].id} in workspace {parent_workspace_id}."
                                )

                            workspace_address_spaces = resource_to_send.properties.get("address_spaces", [])
                            if address_to_free and isinstance(workspace_address_spaces, list):
                                resource_to_send.properties["address_spaces"] = [
                                    a for a in workspace_address_spaces if a != address_to_free
                                ]
                    else:
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
                    await send_deployment_message(
                        content=content,
                        correlation_id=operation.id,
                        session_id=resource_to_send.id,
                        action=next_step.resourceAction,
                    )
                except AddressSpaceConflictError as e:
                    logger.error(f"[ADDRESS_SPACE_CONFLICT] {e}")
                    next_step.message = f"Terminal address space conflict: {e}"
                    next_step.status = Status.UpdatingFailed
                    await self.update_overall_operation_status(operation, next_step, is_last_step=True)
                    await self.operations_repo.update_item(operation)
                    main_step = next(
                        (op_step for op_step in operation.steps
                         if op_step.templateStepId == "main"
                         and op_step.resourceId == operation.resourceId),
                        None
                    )
                    if main_step:
                        primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                        primary_resource.deploymentStatus = Status.DeletingFailed
                        await self.resource_repo.update_item(primary_resource)
                    return True
                except Exception as e:
                    logger.exception("Unable to send update for resource in pipeline step")
                    if next_step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID:
                        if is_final_delivery:
                            next_step.message = f"Failed to enqueue address space cleanup after {MAX_CLEANUP_DELIVERY_COUNT} deliveries: {e}"
                            next_step.status = Status.UpdatingFailed
                            await self.update_overall_operation_status(operation, next_step, is_last_step=True)
                            await self.operations_repo.update_item(operation)
                            main_step = next(
                                (op_step for op_step in operation.steps
                                 if op_step.templateStepId == "main"
                                 and op_step.resourceId == operation.resourceId),
                                None
                            )
                            if main_step:
                                primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                                primary_resource.deploymentStatus = Status.DeletingFailed
                                await self.resource_repo.update_item(primary_resource)
                            return True
                        else:
                            next_step.status = Status.AwaitingUpdate
                            next_step.message = f"Failed to enqueue address space cleanup, will retry: {e}"
                            operation.status = Status.PipelineRunning
                            await self.operations_repo.update_item(operation)
                            return False
                    next_step.message = repr(e)
                    next_step.status = Status.UpdatingFailed
                    await self.update_overall_operation_status(operation, next_step, is_last_step)
                    await self.operations_repo.update_item(operation)
                    return True

                # Post-send persistence: send succeeded, now update operation status for cleanup step
                if next_step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID:
                    for attempt in range(MAX_CLEANUP_RETRIES):
                        try:
                            next_step.status = Status.Updating
                            next_step.updatedWhen = get_timestamp()
                            await self.operations_repo.update_item(operation)
                            break
                        except CosmosAccessConditionFailedError:
                            if attempt == MAX_CLEANUP_RETRIES - 1:
                                logger.warning(
                                    f"ETag conflict persisting {Status.Updating} status for cleanup step {next_step.id} "
                                    f"in operation {operation.id} after successful dispatch."
                                )
                            else:
                                logger.warning(
                                    f"ETag conflict persisting {Status.Updating} status for cleanup step {next_step.id}. "
                                    f"Retrying (attempt {attempt + 1}/{MAX_CLEANUP_RETRIES})..."
                                )
                                try:
                                    fresh_op = await self.operations_repo.get_operation_by_id(operation.id)
                                    self._merge_operation_steps(
                                        in_memory_op=operation,
                                        fresh_op=fresh_op,
                                        step_id_to_update=next_step.id,
                                        step_status=Status.Updating,
                                        step_message=next_step.message or "",
                                    )
                                    await self.operations_repo.update_item(fresh_op)
                                    operation = fresh_op
                                    break
                                except Exception:
                                    pass
                        except Exception as post_send_err:
                            if attempt == MAX_CLEANUP_RETRIES - 1:
                                logger.error(
                                    f"Failed to persist {Status.Updating} status for address space cleanup step {next_step.id} "
                                    f"in operation {operation.id} after successful dispatch: {post_send_err}",
                                    exc_info=True
                                )
                            else:
                                logger.warning(
                                    f"Transient error persisting {Status.Updating} status for cleanup step {next_step.id}. "
                                    f"Retrying (attempt {attempt + 1}/{MAX_CLEANUP_RETRIES})..."
                                )

            result = True

        except EntityDoesNotExist:
            # Marking as true as this message will never succeed anyways and should be removed from the queue.
            result = True
            logger.exception(strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(message.id))
            if operation is not None and step_to_update is not None:
                try:
                    step_to_update.status = (
                        Status.UpdatingFailed if operation.action == RequestAction.Upgrade
                        else Status.DeletingFailed if operation.action == RequestAction.UnInstall
                        else Status.DeploymentFailed
                    )
                    step_to_update.message = f"Resource {message.id} not found in database: operation aborted."
                    await self.update_overall_operation_status(operation, step_to_update, is_last_step=True)
                    await self.operations_repo.update_item(operation)
                except Exception:
                    logger.exception(f"Failed to persist terminal failure status for operation {operation.id} when resource {message.id} was missing")
        except Exception:
            logger.exception("Failed to update status")

        return result

    def _merge_operation_steps(
        self,
        in_memory_op: Operation,
        fresh_op: Operation,
        step_id_to_update: str,
        step_status: Status,
        step_message: str,
    ) -> Tuple[OperationStep, bool, int]:
        """
        Merges in-memory appended steps (e.g. dynamically appended cleanup step on legacy operations)
        into the fresh operation reloaded from Cosmos DB during an ETag conflict retry.
        Recomputes step_to_update, is_last_step, and current_step_index for fresh_op.
        """
        if fresh_op.steps is None:
            fresh_op.steps = []

        if in_memory_op.steps:
            fresh_step_ids = {s.id for s in fresh_op.steps}
            for s in in_memory_op.steps:
                if s.id not in fresh_step_ids:
                    fresh_op.steps.append(s)
                    fresh_step_ids.add(s.id)

        step_to_update = None
        current_step_index = 0
        is_last_step = False
        for i, s in enumerate(fresh_op.steps):
            if s.id == step_id_to_update:
                step_to_update = s
                current_step_index = i
                if i == (len(fresh_op.steps) - 1):
                    is_last_step = True
                break

        if step_to_update is None:
            raise Exception(f"Error finding step {step_id_to_update} in reloaded operation {fresh_op.id}")

        step_to_update.status = step_status
        step_to_update.message = step_message
        step_to_update.updatedWhen = get_timestamp()

        return step_to_update, is_last_step, current_step_index

    def _is_workspace_service_with_address_space(self, resource: dict) -> bool:
        return (resource.get("resourceType") in (ResourceType.WorkspaceService, ResourceType.WorkspaceService.value)
                and bool(resource.get("properties", {}).get("address_space"))
                and bool(resource.get("workspaceId")))

    def _has_workspace_upgrade_step(self, operation: Operation, current_step_index: int) -> bool:
        return any(
            step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID
            for step in operation.steps[current_step_index + 1:]
        )

    def _is_cleanup_completed(self, operation: Operation) -> bool:
        for step in operation.steps:
            if step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID:
                if step.message == strings.ADDRESS_SPACE_CLEANUP_SUCCESS:
                    return True
        if operation.action == RequestAction.UnInstall and operation.status == Status.Deleted:
            if any(step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID for step in operation.steps):
                return True
        return False

    def _is_cleanup_failed(self, operation: Operation) -> bool:
        for step in operation.steps:
            if step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID:
                if step.is_failure() or step.status == Status.UpdatingFailed:
                    return True
        if operation.action == RequestAction.UnInstall and operation.status == Status.DeletingFailed:
            if any(step.templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID for step in operation.steps):
                return True
        return False

    def _is_cleanup_terminal(self, operation: Operation) -> bool:
        return self._is_cleanup_completed(operation) or self._is_cleanup_failed(operation)

    def _create_workspace_upgrade_step(self, resource: dict) -> OperationStep:
        return OperationStep(
            id=str(uuid.uuid4()),
            templateStepId=strings.ADDRESS_SPACE_CLEANUP_STEP_ID,
            stepTitle="Update workspace address spaces",
            resourceId=resource["workspaceId"],
            resourceTemplateName="",
            resourceType=ResourceType.Workspace,
            resourceAction=RequestAction.Upgrade,
            status=Status.AwaitingUpdate,
            sourceTemplateResourceId=resource["id"]
        )

    async def _get_address_cleanup_details(self, operation: Operation) -> Optional[Tuple[str, str, str, dict]]:
        main_step = next(
            (step for step in operation.steps
             if step.templateStepId == "main"
             and step.resourceId == operation.resourceId
             and step.is_success()),
            None
        )
        if main_step is None:
            return None
        resource_to_persist = await self.resource_repo.get_resource_dict_by_id(main_step.resourceId)
        if resource_to_persist.get("resourceType") not in (ResourceType.WorkspaceService, ResourceType.WorkspaceService.value):
            return None

        address_to_free = resource_to_persist.get("properties", {}).get("address_space")
        parent_workspace_id = resource_to_persist.get("workspaceId")
        resource_id = resource_to_persist.get("id")

        if not address_to_free or not parent_workspace_id:
            return None

        return address_to_free, parent_workspace_id, resource_id, resource_to_persist

    async def _free_workspace_address_space(self, operation: Operation) -> bool:
        """
        Frees the address space owned by the uninstalled WorkspaceService after
        the corresponding workspace upgrade has succeeded.
        """
        address_to_free = parent_workspace_id = resource_id = "<unknown>"
        try:
            cleanup_details = await self._get_address_cleanup_details(operation)
            if cleanup_details is None:
                return True

            address_to_free, parent_workspace_id, resource_id, service_dict = cleanup_details

            # Check if cleanup for this step was already completed (idempotency on redelivery)
            if self._is_cleanup_completed(operation):
                return True

            # Check if the uninstalled service already has the address_space_freed marker
            if service_dict.get("properties", {}).get("address_space_freed"):
                return True
            # Check if address_to_free has been assigned to another active workspace service on this workspace (fail closed)
            workspace_services_repo = getattr(self, "workspace_services_repo", None)
            if workspace_services_repo is None:
                from db.repositories.workspace_services import WorkspaceServiceRepository
                workspace_services_repo = await WorkspaceServiceRepository.create()

            active_services = await workspace_services_repo.get_active_workspace_services_for_workspace(parent_workspace_id)
            conflicting_services = [s for s in active_services if s.id != resource_id and s.properties.get("address_space") == address_to_free]
            if conflicting_services:
                raise AddressSpaceConflictError(
                    f"Address space {address_to_free} is allocated to active service {conflicting_services[0].id} in workspace {parent_workspace_id}."
                )

            for attempt in range(MAX_CLEANUP_RETRIES):
                try:
                    workspace = await self.workspace_repo.get_workspace_by_id(parent_workspace_id)
                    workspace_address_spaces = workspace.properties.get("address_spaces") or []
                    if not isinstance(workspace_address_spaces, list) or address_to_free not in workspace_address_spaces:
                        service_dict["properties"]["address_space_freed"] = True
                        await self.resource_repo.update_item_dict(service_dict)
                        return True
                    new_address_spaces = [a for a in workspace_address_spaces if a != address_to_free]
                    workspace_patch = ResourcePatch()
                    workspace_patch.properties = {"address_spaces": new_address_spaces}

                    # Note: patch_workspace with force_version_update=False updates the Cosmos DB record only;
                    # it does not trigger an independent deployment operation. Infrastructure updates (Terraform)
                    # are driven by the trailing workspace upgrade step in the uninstall pipeline.
                    await self.workspace_repo.patch_workspace(
                        workspace,
                        workspace_patch,
                        workspace.etag,
                        self.resource_template_repo,
                        self.resource_history_repo,
                        operation.user,
                        False
                    )
                    service_dict["properties"]["address_space_freed"] = True
                    await self.resource_repo.update_item_dict(service_dict)
                    logger.info(f"Freed address space {address_to_free} from workspace {parent_workspace_id} after successful workspace upgrade for {resource_id}")
                    return True
                except CosmosAccessConditionFailedError:
                    if attempt == MAX_CLEANUP_RETRIES - 1:
                        raise
                    logger.warning(f"ETag conflict when freeing workspace address space after successful workspace upgrade. Retrying (attempt {attempt + 1}/{MAX_CLEANUP_RETRIES})...")
        except AddressSpaceConflictError:
            raise
        except Exception as e:
            logger.error(f"[ADDRESS_SPACE_CLEANUP_FAILED] Failed to free workspace address space {address_to_free} for workspace {parent_workspace_id} after upgrading the workspace for {resource_id}: {e}", exc_info=True)
            return False

        return False

    async def update_overall_operation_status(self, operation: Operation, step: OperationStep, is_last_step: bool):
        operation.updatedWhen = get_timestamp()

        # if it's a one step operation, just replicate the status
        if len(operation.steps) == 1:
            operation.status = step.status
            operation.message = step.message
            return

        # If address space cleanup has completed for an uninstall, only finalize as Deleted if it is the last step and all steps succeeded
        if self._is_cleanup_completed(operation) and operation.action == RequestAction.UnInstall:
            if is_last_step and all(op_step.is_success() for op_step in operation.steps):
                operation.status = Status.Deleted
                operation.message = "Multi step pipeline completed successfully"
                return

        # If address space cleanup has failed terminally for an uninstall, do not reopen to PipelineRunning
        if self._is_cleanup_failed(operation) and operation.action == RequestAction.UnInstall:
            operation.status = Status.DeletingFailed
            operation.message = f"Multi step pipeline failed on step {strings.ADDRESS_SPACE_CLEANUP_STEP_ID}"
            main_step = next(
                (op_step for op_step in operation.steps
                 if op_step.templateStepId == "main" and op_step.resourceId == operation.resourceId),
                None
            )
            if main_step:
                primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                if primary_resource.deploymentStatus != operation.status:
                    primary_resource.deploymentStatus = operation.status
                    await self.resource_repo.update_item(primary_resource)
            return

        operation.status = Status.PipelineRunning
        operation.message = "Multi step pipeline running. See steps for details."

        if step.is_failure():
            operation.status = self.get_failure_status_for_action(operation.action)
            operation.message = f"Multi step pipeline failed on step {step.templateStepId}"

            # pipeline failed - update the primary resource (from the main step) as failed too
            main_step = None
            for op_step in operation.steps:
                if op_step.templateStepId == "main" and op_step.resourceId == operation.resourceId:
                    main_step = op_step
                    break

            if main_step:
                primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                primary_resource.deploymentStatus = operation.status
                await self.resource_repo.update_item(primary_resource)

        if step.is_success() and is_last_step:
            if all(op_step.is_success() for op_step in operation.steps):
                operation.status = self.get_success_status_for_action(operation.action)
                operation.message = "Multi step pipeline completed successfully"

            # pipeline succeeded - update the primary resource (from the main step) as succeeded too
            main_step = None
            for op_step in operation.steps:
                if op_step.templateStepId == "main" and op_step.resourceId == operation.resourceId:
                    main_step = op_step
                    break

            if main_step:
                primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                primary_resource.deploymentStatus = operation.status
                await self.resource_repo.update_item(primary_resource)

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
