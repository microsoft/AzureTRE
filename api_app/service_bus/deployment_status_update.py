import json
import logging
from contextlib import asynccontextmanager

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from pydantic import ValidationError, parse_obj_as

from api.dependencies.database import get_db_client
from db.repositories.operations import OperationRepository
from core import config
from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.operation import DeploymentStatusUpdateMessage, Operation, Status
from resources import strings


@asynccontextmanager
async def default_credentials():
    """
    Context manager which yields the default credentials.
    """
    credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
    yield credential
    await credential.close()


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


def create_updated_operation_document(operation: Operation, message: DeploymentStatusUpdateMessage) -> Operation:
    """Take an operation document and update it with the message contents

    Args:
        operation ([Operation]): Operation representing a document to update
        message ([DeploymentStatusUpdateMessage]): Message which contains the updated information

    Returns:
        [Operation]: Updated Operation object to persist
    """
    previous_state = operation.status
    new_state = message.status

    # Cannot change terminal states
    terminal_states = set([Status.DeletingFailed, Status.Deleted, Status.ActionSucceeded, Status.ActionFailed])
    if previous_state in terminal_states:
        return operation

    # Can only transition from deployed(deleting, failed) to deleted or failed to delete.
    states_that_can_only_transition_to_deleted = set([Status.Failed, Status.Deployed, Status.Deleting])
    deletion_states = set([Status.Deleted, Status.DeletingFailed])
    if previous_state in states_that_can_only_transition_to_deleted and new_state not in deletion_states:
        return operation

    # can only transition from invoking_action to action_succeeded or action_failed
    action_end_states = set([Status.ActionSucceeded, Status.ActionFailed])
    if previous_state == Status.InvokingAction and new_state not in action_end_states:
        return operation

    operation.status = message.status
    operation.message = message.message

    return operation


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


def update_status_in_database(resource_repo: ResourceRepository, operations_repo: OperationRepository, message: DeploymentStatusUpdateMessage):
    """Updates the operation and resource document id

    Args:
        operations_repo ([OperationRepository]): Handle to the operations repository
        message ([DeploymentStatusUpdateMessage]): Message which contains the updated information

    Returns:
        [bool]: True if document is updated, False otherwise.
    """
    result = False

    try:
        # update the op
        operation = operations_repo.get_operation_by_id(str(message.operationId))
        operation_to_persist = create_updated_operation_document(operation, message)
        operations_repo.update_operation_status(operation_to_persist.id, operation_to_persist.status, operation_to_persist.message)

        # update the resource to persist any outputs
        resource = resource_repo.get_resource_dict_by_id(message.id)
        resource_to_persist = create_updated_resource_document(resource, message)
        resource_repo.update_item_dict(resource_to_persist)

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
            result = update_status_in_database(resource_repo, operations_repo, message)
            await receive_message_gen.asend(result)
    except StopAsyncIteration:  # the async generator when finished signals end with this exception.
        pass
