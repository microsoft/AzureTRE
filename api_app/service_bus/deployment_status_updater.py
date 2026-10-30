import asyncio
import json
import uuid
import time

from pydantic import ValidationError, TypeAdapter

from api.routes.resource_helpers import get_timestamp
from models.domain.resource import Output
from db.repositories.resources_history import ResourceHistoryRepository
from models.domain.request_action import RequestAction
from db.repositories.resource_templates import ResourceTemplateRepository
from service_bus.helpers import send_deployment_message, update_resource_for_step
from azure.servicebus import NEXT_AVAILABLE_SESSION
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from db.repositories.operations import PENDING_DISPATCH, OperationRepository
from core import config, credentials
from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.operation import DeploymentStatusUpdateMessage, Operation, OperationStep, Status
from resources import strings
from services.logging import logger, tracer

# The API sends the first step message immediately after it writes the operation. An older entry shows that
# the API stopped between the write and the send.
PENDING_DISPATCH_SECONDS = 5 * 60
AWAITING_STATUSES = (Status.AwaitingDeployment, Status.AwaitingUpdate, Status.AwaitingDeletion, Status.AwaitingAction)
NOT_SENT_WITH_SENSITIVE_VALUES = (
    "The API stopped before it recorded the send of this request. The request has sensitive values, which the API "
    "does not store, so the API cannot send it again. If the status does not change, send the request again."
)
NOT_SENT_BEFORE_A_LATER_REQUEST = (
    "The API stopped before it recorded the send of this request, and a later request changed the resource. "
    "The API does not send this request again."
)


class DeploymentStatusUpdater:
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
                try:
                    async with credentials.get_credential_async_context() as credential:
                        async with ServiceBusClient(
                            config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential
                        ) as service_bus_client:
                            client_created_time = time.time()
                            while True:
                                try:
                                    if time.time() - client_created_time > 3600:
                                        logger.info(
                                            "ServiceBusClient has been active for 1 hour. Recreating for freshness..."
                                        )
                                        break

                                    current_time = time.time()
                                    polling_count += 1
                                    if current_time - last_heartbeat_time >= 60:
                                        logger.info(
                                            f"Queue reader heartbeat: Polled {config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE} queue {polling_count} times in the last minute"
                                        )
                                        last_heartbeat_time = current_time
                                        polling_count = 0

                                    logger.debug(
                                        f"Looking for new messages on {config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE} queue..."
                                    )
                                    # max_wait_time=1 -> don't hold the session open after processing of the message has finished
                                    async with service_bus_client.get_queue_receiver(
                                        queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE,
                                        max_wait_time=1,
                                        session_id=NEXT_AVAILABLE_SESSION,
                                    ) as receiver:
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
                    await asyncio.sleep(10)

                except asyncio.CancelledError:
                    raise

                except Exception as e:
                    logger.exception(f"Unknown exception. Will retry - {e}")
                    await asyncio.sleep(10)

    async def resend_pending_dispatches(self):
        """At start and every 5 minutes, send the first step messages that the API wrote but did not send."""
        while True:
            try:
                sent_before = get_timestamp() - PENDING_DISPATCH_SECONDS
                documents = await self.operations_repo.get_operations_with_pending_dispatch(sent_before)
            except Exception:
                logger.exception("Unable to read the pending first step messages")
                documents = []
            for document in documents:
                try:
                    await self.resend_pending_dispatch(document)
                except Exception:
                    # The entry stays, so the next pass tries again.
                    logger.exception(f"Unable to send the pending message of operation {document.get('id')}")
            await asyncio.sleep(PENDING_DISPATCH_SECONDS)

    async def resend_pending_dispatch(self, document: dict):
        pending = document[PENDING_DISPATCH]
        # Each API instance runs this task. The claim lets one instance send the message.
        if not await self.operations_repo.claim_pending_dispatch(document):
            return
        operation = TypeAdapter(Operation).validate_python(document)
        step = next((item for item in operation.steps if item.id == pending["stepId"]), None)
        if step is None or step.status not in AWAITING_STATUSES:
            # The resource processor sent a status for the step, so it has the message.
            await self.operations_repo.clear_pending_dispatch(operation.id, pending["messageId"])
            return

        # A later request on the resource, or a cascade from a parent with a step for it, for example a delete of a
        # resource whose install was not sent. The install must not come after it.
        if await self.operations_repo.get_later_operations_for_resource(operation.resourceId, operation.createdWhen):
            logger.warning(f"Operation {operation.id} was not sent before a later request. Failing step {step.id}")
            await self.fail_pending_step(operation, step, NOT_SENT_BEFORE_A_LATER_REQUEST, write_resource=False)
            return

        # If an install or an update set a sensitive property, the first message has the real value, and Cosmos DB
        # keeps a placeholder. The updater cannot build that message again. Other first messages have the same
        # values as Cosmos DB, so a resend has the same values as the first send.
        if pending.get("sensitiveValues") and step.resourceId == operation.resourceId:
            logger.warning(f"Operation {operation.id} was not sent and has sensitive values. Failing step {step.id}")
            await self.fail_pending_step(operation, step, NOT_SENT_WITH_SENSITIVE_VALUES)
            return

        try:
            resource_to_send = await update_resource_for_step(
                operation_step=step,
                resource_repo=self.resource_repo,
                resource_template_repo=self.resource_template_repo,
                resource_history_repo=self.resource_history_repo,
                root_resource=None,
                step_resource=None,
                resource_to_update_id=step.resourceId,
                primary_action=operation.action,
                user=operation.user,
            )
            payload = resource_to_send.get_resource_request_message_payload(
                operation_id=operation.id, step_id=step.id, action=step.resourceAction
            )
        except Exception as e:
            logger.exception(f"Unable to build the pending message of operation {operation.id}")
            await self.fail_pending_step(operation, step, repr(e))
            return

        logger.info(f"Sending the pending first step message of operation {operation.id}, step {step.id}")
        await send_deployment_message(
            content=json.dumps(payload),
            correlation_id=operation.id,
            session_id=resource_to_send.id,
            action=step.resourceAction,
            message_id=pending["messageId"],
        )
        await self.operations_repo.clear_pending_dispatch(operation.id, pending["messageId"])

    async def fail_pending_step(
        self, operation: Operation, step: OperationStep, message: str, write_resource: bool = True
    ):
        """Fail a step that the API did not send. The step did not run, so only its request fails."""
        step.status = self.get_failure_status_for_action(step.resourceAction)
        step.message = message
        step.updatedWhen = get_timestamp()
        operation.status = self.get_failure_status_for_action(operation.action)
        operation.message = message
        operation.updatedWhen = step.updatedWhen
        # The Operation model has no pending dispatch, so this write also removes the entry.
        await self.operations_repo.update_item(operation)
        if not write_resource:
            # A later request changes the resource, so it owns the status of the resource.
            return
        # Only the resource of the request shows the failure. A first step on another resource, for example the
        # firewall or the parent workspace, did not run, so that resource keeps its status.
        try:
            resource = await self.resource_repo.get_resource_by_id(uuid.UUID(operation.resourceId))
        except EntityDoesNotExist:
            logger.warning(f"Resource {operation.resourceId} of operation {operation.id} does not exist")
            return
        resource.deploymentStatus = operation.status
        await self.resource_repo.update_item(resource)

    async def process_message(self, msg):
        complete_message = False
        message = ""

        with tracer.start_as_current_span("process_message") as current_span:
            try:
                message = TypeAdapter(DeploymentStatusUpdateMessage).validate_python(json.loads(str(msg)))

                current_span.set_attribute("step_id", message.stepId)
                current_span.set_attribute("operation_id", message.operationId)
                current_span.set_attribute("status", message.status)

                logger.info(f"Received and parsed JSON for: {msg.correlation_id}")
                complete_message = await self.update_status_in_database(message)
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

            if self.ignore_repeated_status(operation, step_to_update, message):
                return True

            uninstall_operation = operation.action == RequestAction.UnInstall
            uninstall_pending_status = Status.PipelineRunning if len(operation.steps) > 1 else Status.Deleting
            if uninstall_operation and self.ignore_uninstall_callback(operation, current_step_index, message):
                if (
                    not step_to_update.statusUpdateComplete
                    and step_to_update.status == message.status
                    and operation.status == Status.DeletingFailed
                    and any(later.is_failure() for later in operation.steps[current_step_index + 1 :])
                ):
                    # Dispatch can fail after the current step succeeds. Repair
                    # a missed root write without replaying the earlier effects.
                    await self.update_primary_uninstall_status(operation)
                    step_to_update.statusUpdateComplete = True
                    await self.operations_repo.update_item(operation)
                return True

            # update the step status
            if step_to_update.status != message.status:
                step_to_update.statusUpdateComplete = False
            step_to_update.status = message.status
            step_to_update.message = message.message
            step_to_update.updatedWhen = get_timestamp()
            if message.executionId is not None:
                step_to_update.executionId = message.executionId
            # Repeated runs make the final status complete only after its writes and dispatch.
            track_completion = uninstall_operation or message.executionId is not None

            # update the overall headline operation status
            await self.update_overall_operation_status(operation, step_to_update, is_last_step)
            if uninstall_operation and is_last_step and step_to_update.is_success():
                # The callback succeeded, but its outputs are not saved yet.
                # Keep polling active if that write fails and needs redelivery.
                operation.status = uninstall_pending_status
                operation.message = "Uninstall outputs are being saved."

            # save the operation
            await self.operations_repo.update_item(operation)
            logger.info(f"Update status in DB for {message.operationId} - {message.status}")

            # copy the step status to the resource item, for convenience
            resource_id = uuid.UUID(step_to_update.resourceId)
            primary_status = (
                uninstall_pending_status if uninstall_operation and step_to_update.is_success() else operation.status
            )

            resource = await self.resource_repo.get_resource_by_id(resource_id)
            resource.deploymentStatus = (
                primary_status
                if uninstall_operation and str(resource_id) == operation.resourceId
                else step_to_update.status
            )
            await self.resource_repo.update_item(resource)
            if uninstall_operation and str(resource_id) != operation.resourceId:
                await self.update_primary_uninstall_status(operation, primary_status)

            # if the step failed, or this queue message is an intermediary ("now deploying..."), return here.
            if not step_to_update.is_success():
                if track_completion and step_to_update.is_failure():
                    step_to_update.statusUpdateComplete = True
                    await self.operations_repo.update_item(operation)
                return True

            # update the resource doc to persist any outputs
            resource = await self.resource_repo.get_resource_dict_by_id(resource_id)
            resource_to_persist = self.create_updated_resource_document(resource, message)
            await self.resource_repo.update_item_dict(resource_to_persist)

            if uninstall_operation and is_last_step:
                # Publish success only after saving the final outputs. Keep the
                # root visible if the operation write still needs redelivery.
                await self.update_overall_operation_status(operation, step_to_update, is_last_step)
                await self.operations_repo.update_item(operation)
                await self.update_primary_uninstall_status(operation)

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
                        user=operation.user,
                    )

                    # create + send the message
                    logger.info(
                        f"Sending next step in operation to deployment queue -> step_id: {next_step.templateStepId}, action: {next_step.resourceAction}"
                    )
                    content = json.dumps(
                        resource_to_send.get_resource_request_message_payload(
                            operation_id=operation.id, step_id=next_step.id, action=next_step.resourceAction
                        )
                    )
                    await send_deployment_message(
                        content=content,
                        correlation_id=operation.id,
                        session_id=resource_to_send.id,
                        action=next_step.resourceAction,
                    )
                except Exception as e:
                    logger.exception("Unable to send update for resource in pipeline step")
                    next_step.message = repr(e)
                    next_step.status = Status.UpdatingFailed
                    await self.update_overall_operation_status(operation, next_step, is_last_step)
                    await self.operations_repo.update_item(operation)
                    if uninstall_operation:
                        await self.update_primary_uninstall_status(operation)

            if track_completion:
                # Save only after the resource writes and dispatch. A retry must
                # resume those effects if an earlier database write succeeded.
                step_to_update.statusUpdateComplete = True
                await self.operations_repo.update_item(operation)

            result = True

        except EntityDoesNotExist:
            # Marking as true as this message will never succeed anyways and should be removed from the queue.
            result = True
            logger.exception(strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(message.id))
        except Exception:
            logger.exception("Failed to update status")

        return result

    def ignore_repeated_status(
        self, operation: Operation, step: OperationStep, message: DeploymentStatusUpdateMessage
    ) -> bool:
        """
        Service Bus can give a step to a second resource processor worker. Keep the first final status of the step.
        A message without an execution ID comes from an older resource processor, so the earlier rules apply to it.
        """
        if message.executionId is None or not (step.is_success() or step.is_failure()):
            return False
        if step.executionId is None:
            # The API or an older resource processor wrote this final status. The first run of the step replaces it,
            # for example after the API failed a step whose message the resource processor still got.
            return False
        if step.executionId != message.executionId:
            logger.info(f"Ignoring a status from another run of step {operation.id}/{step.id}")
            return True
        if message.status != step.status:
            logger.info(f"Ignoring a later status from the run that finished step {operation.id}/{step.id}")
            return True
        if step.statusUpdateComplete:
            logger.info(f"Ignoring a repeated final status for step {operation.id}/{step.id}")
            return True
        # The earlier copy stopped before all of its writes. Process this copy to finish them.
        return False

    def ignore_uninstall_callback(self, operation: Operation, step_index: int, message: DeploymentStatusUpdateMessage):
        step = operation.steps[step_index]
        if step.is_success() or step.is_failure():
            if step.status != message.status or step.statusUpdateComplete:
                logger.info(f"Ignoring completed uninstall callback for {operation.id}/{step.id}")
                return True

        # Dispatch follows the previous resource writes. Once a later step has
        # progressed, replaying those writes could overwrite newer resource data.
        awaiting = (Status.AwaitingDeployment, Status.AwaitingUpdate, Status.AwaitingDeletion, Status.AwaitingAction)
        if any(later.status not in awaiting for later in operation.steps[step_index + 1 :]):
            logger.info(f"Ignoring earlier uninstall callback for {operation.id}/{step.id}")
            return True

        if any(not previous.is_success() for previous in operation.steps[:step_index]):
            logger.info(f"Ignoring uninstall callback before its predecessors succeeded: {operation.id}/{step.id}")
            return True
        return False

    async def update_primary_uninstall_status(self, operation: Operation, status: Status | None = None):
        # Cascaded deletion can contain several main steps. The operation owns
        # the root resource, which must remain visible until every step finishes.
        primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(operation.resourceId))
        primary_resource.deploymentStatus = operation.status if status is None else status
        await self.resource_repo.update_item(primary_resource)

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

            # Uninstall pipelines persist the root status in the caller. Keep
            # the existing main-step behaviour for other pipeline actions.
            if operation.action != RequestAction.UnInstall:
                main_step = next((item for item in operation.steps if item.templateStepId == "main"), None)
                if main_step:
                    primary_resource = await self.resource_repo.get_resource_by_id(uuid.UUID(main_step.resourceId))
                    primary_resource.deploymentStatus = operation.status
                    await self.resource_repo.update_item(primary_resource)
            return

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
            if obj_type == "string" and isinstance(value, str):
                value = value.strip("'").strip('"')
            elif obj_type == "boolean":
                if isinstance(value, str):
                    value = value.strip("'").strip('"')
                value = value.lower() == "true"

            result_dict[name] = value

        return result_dict
