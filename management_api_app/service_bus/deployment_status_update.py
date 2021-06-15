import json
import logging
from json import JSONDecodeError

from fastapi import FastAPI

from azure.servicebus.aio import ServiceBusClient
from azure.identity.aio import DefaultAzureCredential

from core import config
from db.errors import EntityDoesNotExist
from resources import strings
from api.dependencies.database import get_db_client
from db.repositories.workspaces import WorkspaceRepository


async def receive_message():
    credential = DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID)
    service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

    async with service_bus_client:
        receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE)
        async with receiver:
            received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=5)
            for msg in received_msgs:
                try:
                    message = json.loads(str(msg))
                    yield message
                except JSONDecodeError:
                    logging.error(strings.DEPLOYMENT_STATUS_MESSAGE_FORMAT_INCORRECT)
                await receiver.complete_message(msg)
        await credential.close()


async def update_status_in_database(app, message):
    workspace_repo = WorkspaceRepository(get_db_client(app))
    try:
        workspace = workspace_repo.get_workspace_by_workspace_id(message.id)
        workspace["deployment"]["status"] = message.status
        workspace["deployment"]["message"] = message.message
        workspace_repo.update_workspace(workspace)
    except EntityDoesNotExist:
        logging.debug("id was not found")
    except ValueError:
        logging.debug("message is not formatted correctly")


async def receive_message_and_update_deployment(app: FastAPI) -> None:
    """
    Receives messages from the deployment status update queue and updates the status for
    the associated resource in the state store.
    """
    async for message in receive_message():
        print(message)
