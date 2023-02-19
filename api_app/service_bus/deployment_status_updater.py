import asyncio
import json
import logging
import uuid

from pydantic import ValidationError, parse_obj_as

from api.dependencies.database import get_db_client
from api.routes.resource_helpers import get_timestamp
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


class DeploymentStatusUpdater():
    def __init__(self, app):
        self.app = app

    async def init_repos(self):
        db_client = await get_db_client(self.app)
        self.operations_repo = await OperationRepository.create(db_client)
        self.resource_repo = await ResourceRepository.create(db_client)
        self.resource_template_repo = await ResourceTemplateRepository.create(db_client)
        self.resource_history_repo = await ResourceHistoryRepository.create(db_client)

    def run(self, *args, **kwargs):
        asyncio.run(self.receive_messages())

    async def receive_messages(self):
        while True:
            try:
                async with credentials.get_credential_async() as credential:
                    service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

                    logging.info("Looking for new session...")
                    # max_wait_time=1 -> don't hold the session open after processing of the message has finished
                    async with service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE, max_wait_time=1, session_id=NEXT_AVAILABLE_SESSION) as receiver:
                        logging.info(f"Got a session containing messages: {receiver.session.session_id}")
                        async with AutoLockRenewer() as renewer:
                            renewer.register(receiver, receiver.session, max_lock_renewal_duration=60)
                            async for msg in receiver:
                                complete_message = await self.process_message(msg)
                                if complete_message:
                                    await receiver.complete_message(msg)
                                else:
                                    # could have been any kind of transient issue, we'll abandon back to the queue, and retry
                                    await receiver.abandon_message(msg)
                        logging.info(f"Closing session: {receiver.session.session_id}")

            except OperationTimeoutError:
                # Timeout occurred whilst connecting to a session - this is expected and indicates no non-empty sessions are available
                logging.debug("No sessions for this process. Will look again...")

            except ServiceBusConnectionError:
                # Occasionally there will be a transient / network-level error in connecting to SB.
                logging.info("Unknown Service Bus connection error. Will retry...")

            except Exception as e:
                # Catch all other exceptions, log them via .exception to get the stack trace, and reconnect
                logging.exception(f"Unknown exception. Will retry - {e}")

    async def process_message(self, msg):
        complete_message = False
        message = ""

        try:
            message = parse_obj_as(DeploymentStatusUpdateMessage, json.loads(str(msg)))
            logging.info(f"Received and parsed JSON for: {msg.correlation_id}")
            complete_message = await self.update_status_in_database(message)
            logging.info(f"Update status in DB for {message.operationId} - {message.status}")
        except (json.JSONDecodeError, ValidationError):
            logging.exception(f"{strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT}: {msg.correlation_id}")
        except Exception:
            logging.exception(f"Exception processing message: {msg.correlation_id}")

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
                if step.stepId == message.stepId and step.resourceId == str(message.id):
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

            # more steps in the op to do?
            if is_last_step is False:
                assert current_step_index < (len(operation.steps) - 1)
                next_step = operation.steps[current_step_index + 1]

                # catch any errors in updating the resource - maybe Cosmos / schema invalid etc, and report them back to the op
                try:
                    # parent resource is always retrieved via cosmos, hence it is always with redacted sensitive values
                    parent_resource = await self.resource_repo.get_resource_by_id(next_step.parentResourceId)
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
                    logging.info(f"Sending next step in operation to deployment queue -> step_id: {next_step.stepId}, action: {next_step.resourceAction}")
                    content = json.dumps(resource_to_send.get_resource_request_message_payload(operation_id=operation.id, step_id=next_step.stepId, action=next_step.resourceAction))
                    await send_deployment_message(content=content, correlation_id=operation.id, session_id=resource_to_send.id, action=next_step.resourceAction)
                except Exception as e:
                    logging.exception("Unable to send update for resource in pipeline step")
                    next_step.message = repr(e)
                    next_step.status = Status.UpdatingFailed
                    await self.update_overall_operation_status(operation, next_step, is_last_step)
                    await self.operations_repo.update_item(operation)

            result = True

        except EntityDoesNotExist:
            # Marking as true as this message will never succeed anyways and should be removed from the queue.
            result = True
            logging.exception(strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(message.id))
        except Exception:
            logging.exception("Failed to update status")

        return result

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
            operation.message = f"Multi step pipeline failed on step {step.stepId}"

            # pipeline failed - update the primary resource (from the main step) as failed too
            main_step = None
            for i, step in enumerate(operation.steps):
                if step.stepId == "main":
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
        output_dict = {output.Name: output.Value.strip("'").strip('"') if isinstance(output.Value, str) else output.Value for output in message.outputs}
        resource["properties"].update(output_dict)

        return resource
