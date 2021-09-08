import json
import logging
from contextlib import asynccontextmanager

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from pydantic import ValidationError, parse_obj_as

from api.dependencies.database import get_db_client
from core import config
from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from models.domain.resource import Status
from models.domain.workspace import DeploymentStatusUpdateMessage
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


def create_updated_deployment_document(resource: dict, message: DeploymentStatusUpdateMessage):
    """Take a workspace and a deployment status update message and updates workspace with the message contents

    Args:
        resource ([dict]): Dictionary representing a resource to update
        message ([DeploymentStatusUpdateMessage]): Message which contains the updated information

    Returns:
        [dict]: Dictionary representing a resource with the deployment sub doc updated
    """
    if resource["deployment"]["status"] in [Status.DeletingFailed, Status.Deleted]:
        return resource  # cannot change terminal states
    if resource["deployment"]["status"] in [Status.Failed, Status.Deployed, Status.Deleting]:
        if message.status not in [Status.Deleted, Status.DeletingFailed]:
            return resource  # can only transitions from deployed(deleting, failed) to deleted or failed to delete.

    resource["deployment"]["status"] = message.status
    resource["deployment"]["message"] = message.message

    # although outputs are likely to be relevant when resources are moving to "deployed" status,
    # lets not limit when we update them and have the resource process make that decision.
    output_dict = {output.Name: output.Value.strip("'").strip('"') for output in message.outputs}

    resource["resourceTemplateParameters"].update(output_dict)

    return resource


def update_status_in_database(resource_repo: ResourceRepository, message: DeploymentStatusUpdateMessage):
    """Updates the deployment sub document with message content

    Args:
        resource_repo ([ResourceRepository]): Handle to the resource repository
        message ([DeploymentStatusUpdateMessage]): Message which contains the updated information

    Returns:
        [bool]: True if document is updated, False otherwise.
    """
    result = False

    try:
        resource = resource_repo.get_resource_dict_by_id(message.id)
        resource_repo.update_item_dict(create_updated_deployment_document(resource, message))
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
            resource_repo = ResourceRepository(get_db_client(app))
            result = update_status_in_database(resource_repo, message)
            await receive_message_gen.asend(result)
    except StopAsyncIteration:  # the async generator when finished signals end with this exception.
        pass
