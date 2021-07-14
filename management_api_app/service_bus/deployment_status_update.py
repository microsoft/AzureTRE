import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import ValidationError, parse_obj_as

from azure.servicebus.aio import ServiceBusClient
from azure.identity.aio import DefaultAzureCredential

from core import config
from resources import strings
from db.errors import EntityDoesNotExist
from api.dependencies.database import get_db_client
from db.repositories.workspaces import WorkspaceRepository
from models.domain.workspace import DeploymentStatusUpdateMessage, Workspace
from models.domain.resource import Status


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


def create_updated_deployment_document(workspace: Workspace, message: DeploymentStatusUpdateMessage):
    """Take a workspace and a deployment status update message and updates workspace with the message contents

    Args:
        workspace ([Workspace]): Workspace to update
        message ([DeploymentStatusUpdateMessage]): Message which contains the updated information

    Returns:
        [Workspace]: Workspace with the deployment sub doc updated
    """
    if workspace.deployment.status == Status.Deployed:
        return workspace  # Never update a deployed workspace.
    workspace.deployment.status = message.status
    workspace.deployment.message = message.message
    return workspace


def update_status_in_database(workspace_repo: WorkspaceRepository, message: DeploymentStatusUpdateMessage):
    """Updates the deployment sub document with message content

    Args:
        workspace_repo ([WorkspaceRepository]): Handle to the workspace repository
        message ([DeploymentStatusUpdateMessage]): Message which contains the updated information

    Returns:
        [bool]: True if document is updated, False otherwise.
    """
    result = False

    try:
        workspace = workspace_repo.get_workspace_by_workspace_id(message.id)
        workspace_repo.update_workspace(create_updated_deployment_document(workspace, message))
        result = True
    except EntityDoesNotExist:
        # Marking as true as this message will never succeed anyways and should be removed from the queue.
        result = True
        error_string = strings.DEPLOYMENT_STATUS_ID_NOT_FOUND.format(message.id)
        logging.error(error_string)
    except Exception as e:
        logging.error(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING + " " + str(e))

    return result


async def receive_message_and_update_deployment(app: FastAPI) -> None:
    """
    Receives messages from the deployment status update queue and updates the status for
    the associated resource in the state store.
    Args:
        app ([FastAPI]): Handle to the currently running app
    """
    receive_message_gen = receive_message()

    try:
        async for message in receive_message_gen:
            workspace_repo = WorkspaceRepository(get_db_client(app))
            result = update_status_in_database(workspace_repo, message)
            await receive_message_gen.asend(result)
    except StopAsyncIteration:  # the async generator when finished signals end with this exception.
        pass
