import json
import logging

from azure.servicebus.aio import ServiceBusClient
from fastapi import HTTPException
from pydantic import ValidationError, parse_obj_as

from api.dependencies.database import get_db_client
from api.dependencies.airlock import get_airlock_request_by_id_from_path
from api.routes.airlock_resource_helpers import update_and_publish_event_airlock_request
from db.repositories.workspaces import WorkspaceRepository
from models.domain.airlock_request import AirlockRequestStatus
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_operations import StepResultStatusUpdateMessage
from core import config, credentials
from resources import strings


async def receive_message_from_step_result_queue():
    """
    This method is an async generator which receives messages from service bus
    and yields those messages. If the yielded function return True the message is
    marked complete.
    """
    async with credentials.get_credential_async() as credential:
        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)

        async with service_bus_client:
            receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_STEP_RESULT_QUEUE)

            async with receiver:
                received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=5)

                for msg in received_msgs:
                    result = True
                    message = ""

                    try:
                        message = json.loads(str(msg))
                        result = (yield parse_obj_as(StepResultStatusUpdateMessage, message))
                    except (json.JSONDecodeError, ValidationError):
                        logging.exception(strings.STEP_RESULT_MESSAGE_FORMAT_INCORRECT)

                    if result:
                        logging.info(f"Received step_result status update message with correlation ID {msg.correlation_id}: {message}")
                        await receiver.complete_message(msg)


async def update_status_in_database(airlock_request_repo: AirlockRequestRepository, workspace_repo: WorkspaceRepository, step_result_message: StepResultStatusUpdateMessage):
    """
    Updates an airlock request and with the new status from step_result message contents.

    """
    result = False
    try:
        step_result_data = step_result_message.data
        airlock_request_id = step_result_data.request_id
        current_status = step_result_data.completed_step
        new_status = AirlockRequestStatus(step_result_data.new_status) if step_result_data.new_status else None
        status_message = step_result_data.status_message
        request_files = step_result_data.request_files
        # Find the airlock request by id
        airlock_request = await get_airlock_request_by_id_from_path(airlock_request_id=airlock_request_id, airlock_request_repo=airlock_request_repo)
        # Validate that the airlock request status is the same as current status
        if airlock_request.status == current_status:
            workspace = await workspace_repo.get_workspace_by_id(airlock_request.workspaceId)
            # update to new status and send to event grid
            await update_and_publish_event_airlock_request(airlock_request=airlock_request, airlock_request_repo=airlock_request_repo, updated_by=airlock_request.updatedBy, workspace=workspace, new_status=new_status, request_files=request_files, status_message=status_message)
            result = True
        else:
            error_string = strings.STEP_RESULT_MESSAGE_STATUS_DOES_NOT_MATCH.format(airlock_request_id, current_status, airlock_request.status)
            logging.error(error_string)
    except HTTPException as e:
        if e.status_code == 404:
            # Marking as true as this message will never succeed anyways and should be removed from the queue.
            result = True
            error_string = strings.STEP_RESULT_ID_NOT_FOUND.format(airlock_request_id)
            logging.exception(error_string)
        if e.status_code == 400:
            result = True
            error_string = strings.STEP_RESULT_MESSAGE_INVALID_STATUS.format(airlock_request_id, current_status, new_status)
            logging.exception(error_string)
        if e.status_code == 503:
            logging.exception(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
    except Exception:
        logging.exception("Failed updating request status")

    return result


async def receive_step_result_message_and_update_status(app) -> None:
    """
    Receives messages from the step result eventgrid topic and updates the status for
    the airlock request in the state store.
    Args:
        app ([FastAPI]): Handle to the currently running app
    """
    receive_message_gen = receive_message_from_step_result_queue()

    try:
        async for message in receive_message_gen:
            db_client = await get_db_client(app)
            airlock_request_repo = await AirlockRequestRepository.create(db_client)
            workspace_repo = await WorkspaceRepository.create(db_client)
            logging.info("Fetched step_result message from queue, start updating airlock request")
            result = await update_status_in_database(airlock_request_repo, workspace_repo, message)
            await receive_message_gen.asend(result)
            logging.info("Finished updating airlock request")
    except StopAsyncIteration:  # the async generator when finished signals end with this exception.
        pass
