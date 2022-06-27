import json
import logging

from azure.servicebus.aio import ServiceBusClient
from fastapi import HTTPException
from pydantic import ValidationError, parse_obj_as

from api.dependencies.database import get_db_client
from api.dependencies.airlock import get_airlock_request_by_id_from_path
from api.routes.airlock_resource_helpers import update_status_and_publish_event_airlock_request
from models.domain.airlock_request import AirlockRequestStatus
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_operations import StepResultStatusUpdateMessage
from service_bus.helpers import default_credentials
from core import config
from db.errors import EntityDoesNotExist
from resources import strings


async def receive_message_from_step_result_queue():
    """
    This method is an async generator which receives messages from service bus
    and yields those messages. If the yielded function return True the message is
    marked complete.
    """
    async with default_credentials() as credential:
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
                    except (json.JSONDecodeError, ValidationError) as e:
                        logging.error(f"{strings.STEP_RESULT_MESSAGE_FORMAT_INCORRECT}: {e}")

                    if result:
                        logging.info(f"Received deployment status update message with correlation ID {msg.correlation_id}: {message}")
                        await receiver.complete_message(msg)


async def update_status_in_database(airlock_request_repo: AirlockRequestRepository, step_result_message: StepResultStatusUpdateMessage):
    """
    If there is another step in the operation after this one, process the substitutions + patch, then enqueue a message to process it.
    """
    result = False
    try:
        step_result_data = step_result_message.data
        airlock_request_id = step_result_data.request_id
        current_status = step_result_data.completed_step
        new_status = AirlockRequestStatus(step_result_data.new_status)
        # Find the airlock request by id
        airlock_request = await get_airlock_request_by_id_from_path(airlock_request_id=airlock_request_id, airlock_request_repo=airlock_request_repo)
        # Validate that the airlock request status is the same as current status
        if airlock_request.status == current_status:
            # update to new status and send to event grid
            await update_status_and_publish_event_airlock_request(airlock_request=airlock_request, airlock_request_repo=airlock_request_repo, user=airlock_request.user, new_status=new_status)
            result = True
        else:
            logging.error(strings.STEP_RESULT_MESSAGE_INVALID_STATUS)
    except EntityDoesNotExist:
        # Marking as true as this message will never succeed anyways and should be removed from the queue.
        result = True
        error_string = strings.STEP_RESULT_ID_NOT_FOUND.format(step_result_message.id)
        logging.error(error_string)
    except HTTPException as e:
        if e.status_code == 400:
            logging.error(strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)
    except Exception as e:
        logging.error(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING + " " + str(e))

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
            airlock_request_repo = AirlockRequestRepository(get_db_client(app))
            result = await update_status_in_database(airlock_request_repo, message)
            await receive_message_gen.asend(result)
    except StopAsyncIteration:  # the async generator when finished signals end with this exception.
        pass
