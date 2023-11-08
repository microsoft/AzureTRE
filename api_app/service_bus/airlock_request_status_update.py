import asyncio
import json
import logging

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from fastapi import HTTPException
from pydantic import ValidationError, parse_obj_as

from api.dependencies.database import get_db_client
from api.dependencies.airlock import get_airlock_request_by_id_from_path
from services.airlock import update_and_publish_event_airlock_request
from db.repositories.workspaces import WorkspaceRepository
from models.domain.airlock_request import AirlockRequestStatus
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_operations import StepResultStatusUpdateMessage
from core import config, credentials
from resources import strings


class AirlockStatusUpdater():

    def __init__(self, app):
        self.app = app

    async def init_repos(self):
        db_client = await get_db_client(self.app)
        self.airlock_request_repo = await AirlockRequestRepository.create(db_client)
        self.workspace_repo = await WorkspaceRepository.create(db_client)

    def run(self, *args, **kwargs):
        asyncio.run(self.receive_messages())

    async def receive_messages(self):
        while True:
            try:
                async with credentials.get_credential_async() as credential:
                    service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)
                    receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_STEP_RESULT_QUEUE)
                    received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=60)
                    for msg in received_msgs:
                        complete_message = await self.process_message(msg)
                        if complete_message:
                            await receiver.complete_message(msg)
                        else:
                            # could have been any kind of transient issue, we'll abandon back to the queue, and retry
                            await receiver.abandon_message(msg)

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

        try:
            message = parse_obj_as(StepResultStatusUpdateMessage, json.loads(str(msg)))
            logging.info(f"Received step_result status update message with correlation ID {message.id}: {message}")
            complete_message = await self.update_status_in_database(message)
            logging.info(f"Update status in DB for {message.id}")
        except (json.JSONDecodeError, ValidationError):
            logging.exception(f"{strings.STEP_RESULT_MESSAGE_FORMAT_INCORRECT}: {msg.correlation_id}")
            complete_message = True
        except Exception:
            logging.exception(f"Exception processing message: {msg.correlation_id}")

        return complete_message

    async def update_status_in_database(self, step_result_message: StepResultStatusUpdateMessage):
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
            airlock_request = await get_airlock_request_by_id_from_path(airlock_request_id=airlock_request_id, airlock_request_repo=self.airlock_request_repo)
            # Validate that the airlock request status is the same as current status
            if airlock_request.status == current_status:
                workspace = await self.workspace_repo.get_workspace_by_id(airlock_request.workspaceId)
                # update to new status and send to event grid
                await update_and_publish_event_airlock_request(airlock_request=airlock_request, airlock_request_repo=self.airlock_request_repo, updated_by=airlock_request.updatedBy, workspace=workspace, new_status=new_status, request_files=request_files, status_message=status_message)
                result = True
            else:
                logging.error(strings.STEP_RESULT_MESSAGE_STATUS_DOES_NOT_MATCH.format(airlock_request_id, current_status, airlock_request.status))
        except HTTPException as e:
            if e.status_code == 404:
                # Marking as true as this message will never succeed anyways and should be removed from the queue.
                result = True
                logging.exception(strings.STEP_RESULT_ID_NOT_FOUND.format(airlock_request_id))
            if e.status_code == 400:
                result = True
                logging.exception(strings.STEP_RESULT_MESSAGE_INVALID_STATUS.format(airlock_request_id, current_status, new_status))
            if e.status_code == 503:
                logging.exception(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
        except Exception:
            logging.exception("Failed updating request status")

        return result
