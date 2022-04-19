import json
import logging

from azure.servicebus.aio import ServiceBusClient
from pydantic import ValidationError, parse_obj_as

from api.dependencies.database import get_db_client
from db.repositories.resource_templates import ResourceTemplateRepository
from service_bus.step_helpers import default_credentials, send_deployment_message, update_resource_for_step
from db.repositories.operations import OperationRepository
from core import config
from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.operation import DeploymentStatusUpdateMessage, OperationStep, Status
from resources import strings


async def receive_message():
    """
    This method is an async generator which receives messages from service bus
    and yields those messages. If the yielded function return True the message is
    marked complete.
    """
    async with default_credentials() as credential:
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

        async with service_bus_client:
            receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE)

            async with receiver:
                received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=5)

                for msg in received_msgs:
                    result = True
                    message = ""

                    try:
                        message = json.loads(str(msg))
                        result = (yield parse_obj_as(DeploymentStatusUpdateMessage, message))
                    except (json.JSONDecodeError, ValidationError) as e:
                        logging.error(f"{strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT}: {e}")

                    if result:
                        logging.info(f"Received deployment status update message with correlation ID {msg.correlation_id}: {message}")
                        await receiver.complete_message(msg)


def update_step_status(step: OperationStep, message: DeploymentStatusUpdateMessage) -> OperationStep:
    """Take an operation step and updates it with the message contents

    Args:
        step ([OperationStep]): Operation step representing a document to update
        message ([DeploymentStatusUpdateMessage]): Message which contains the updated information

    Returns:
        [OperationStep]: Updated step object to persist
    """
    previous_state = step.status
    new_state = message.status

    # Cannot change terminal states
    terminal_states = set([Status.DeletingFailed, Status.Deleted, Status.ActionSucceeded, Status.ActionFailed])
    if previous_state in terminal_states:
        return step

    # Can only transition from deployed(deleting, failed) to deleted or failed to delete.
    states_that_can_only_transition_to_deleted = set([Status.Failed, Status.Deployed, Status.Deleting])
    deletion_states = set([Status.Deleted, Status.DeletingFailed])
    if previous_state in states_that_can_only_transition_to_deleted and new_state not in deletion_states:
        return step

    # can only transition from invoking_action to action_succeeded or action_failed
    action_end_states = set([Status.ActionSucceeded, Status.ActionFailed])
    if previous_state == Status.InvokingAction and new_state not in action_end_states:
        return step

    step.status = message.status
    step.message = message.message

    return step


def create_updated_resource_document(resource: dict, message: DeploymentStatusUpdateMessage):
    """
    Merge the outputs with the resource document to persist
    """

    # although outputs are likely to be relevant when resources are moving to "deployed" status,
    # lets not limit when we update them and have the resource process make that decision.
    output_dict = {output.Name: output.Value.strip("'").strip('"') for output in message.outputs}
    resource["properties"].update(output_dict)

    # if deleted - mark as isActive = False
    if message.status == Status.Deleted:
        resource["isActive"] = False

    return resource


async def update_status_in_database(resource_repo: ResourceRepository, operations_repo: OperationRepository, resource_template_repo: ResourceTemplateRepository, message: DeploymentStatusUpdateMessage):
    result = False

    try:
        # update the op
        operation = operations_repo.get_operation_by_id(str(message.operationId))
        step_to_update = None
        is_last_step = False

        current_step_index = 0
        for i, step in enumerate(operation.steps):
            if step.stepId == message.stepId:
                step_to_update = step
                current_step_index = i
                if i == (len(operation.steps) - 1):
                    is_last_step = True

        if step_to_update is None:
            raise f"Error finding step {message.stepId} in operation {message.operationId}"

        # update the step status
        update_step_status(step_to_update, message)

        # keep the parent operation doc status up to date with the latest step
        # TODO: make this more descriptive and about the stage in the pipeline you're at
        operation.status = step_to_update.status
        operation.message = step_to_update.message

        operations_repo.update_item(operation)

        # if the step failed, or this message is an intermediary ("now deploying..."), return here.
        if not step_to_update.is_success():
            return True

        # update the resource doc to persist any outputs
        resource = resource_repo.get_resource_by_id(step_to_update.resourceId)
        resource_to_persist = create_updated_resource_document(resource.dict(), message)
        resource_repo.update_item_dict(resource_to_persist)

        # more steps in the op to do?
        if is_last_step is False:
            next_step = operation.steps[current_step_index + 1]

            resource_to_send = update_resource_for_step(
                operation_step=next_step,
                resource_repo=resource_repo,
                resource_template_repo=resource_template_repo,
                primary_resource_id=operation.resourceId,
                resource_to_update_id=next_step.resourceId,
                primary_action=operation.action,
                user=operation.user)

            # create + send the message
            logging.info(f"Sending next step in operation to deployment queue -> step_id: {next_step.stepId}, action: {next_step.resourceAction}")
            content = json.dumps(resource_to_send.get_resource_request_message_payload(operation_id=operation.id, step_id=next_step.stepId, action=next_step.resourceAction))
            await send_deployment_message(content=content, correlation_id=operation.id, session_id=resource_to_send.id, action=next_step.resourceAction)

        result = True

    except EntityDoesNotExist:
        # Marking as true as this message will never succeed anyways and should be removed from the queue.
        result = True
        error_string = strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(message.id)
        logging.error(error_string)
    except Exception as e:
        logging.error(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING + " " + str(e))

    return result


async def receive_message_and_update_deployment(app) -> None:
    """
    Receives messages from the deployment status update queue and updates the status for
    the associated resource in the state store.
    Args:
        app ([FastAPI]): Handle to the currently running app
    """
    receive_message_gen = receive_message()

    try:
        async for message in receive_message_gen:
            operations_repo = OperationRepository(get_db_client(app))
            resource_repo = ResourceRepository(get_db_client(app))
            resource_template_repo = ResourceTemplateRepository(get_db_client(app))
            result = await update_status_in_database(resource_repo, operations_repo, resource_template_repo, message)
            await receive_message_gen.asend(result)
    except StopAsyncIteration:  # the async generator when finished signals end with this exception.
        pass
