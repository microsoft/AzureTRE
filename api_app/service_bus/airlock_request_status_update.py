import asyncio
import json
import time

from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from fastapi import HTTPException
from pydantic import ValidationError, parse_obj_as

from api.dependencies.airlock import get_airlock_request_by_id_from_path
from services.airlock import update_and_publish_event_airlock_request
from services.logging import logger, tracer
from db.repositories.workspaces import WorkspaceRepository
from models.domain.airlock_request import AirlockRequestStatus
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_operations import StepResultStatusUpdateMessage
from core import config, credentials
from resources import strings


class AirlockStatusUpdater():

    def __init__(self):
        pass

    async def init_repos(self):
        self.airlock_request_repo = await AirlockRequestRepository.create()
        self.workspace_repo = await WorkspaceRepository.create()

    async def receive_messages(self):
        with tracer.start_as_current_span("airlock_receive_messages"):
            last_heartbeat_time = 0
            polling_count = 0

            while True:
                try:
                    current_time = time.time()
                    polling_count += 1
                    # Log a heartbeat message every 60 seconds to show the service is still working
                    if current_time - last_heartbeat_time >= 60:
                        logger.info(f"Queue reader heartbeat: Polled {config.SERVICE_BUS_STEP_RESULT_QUEUE} queue {polling_count} times in the last minute")
                        last_heartbeat_time = current_time
                        polling_count = 0

                    async with credentials.get_credential_async_context() as credential:
                        service_bus_client = ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential)
                        receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_STEP_RESULT_QUEUE)
                        logger.debug(f"Looking for new messages on {config.SERVICE_BUS_STEP_RESULT_QUEUE} queue...")
                        async with receiver:
                            received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=1)
                            for msg in received_msgs:
                                async with AutoLockRenewer() as renewer:
                                    renewer.register(receiver, msg, max_lock_renewal_duration=60)
                                    complete_message = await self.process_message(msg)
                                    if complete_message:
                                        await receiver.complete_message(msg)
                                    else:
                                        # could have been any kind of transient issue, we'll abandon back to the queue, and retry
                                        await receiver.abandon_message(msg)

                        await asyncio.sleep(10)

                except OperationTimeoutError:
                    # Timeout occurred whilst connecting to a session - this is expected and indicates no non-empty sessions are available
                    logger.debug("No sessions for this process. Will look again...")

                except ServiceBusConnectionError:
                    # Occasionally there will be a transient / network-level error in connecting to SB.
                    logger.info("Unknown Service Bus connection error. Will retry...")

                except Exception as e:
                    # Catch all other exceptions, log them via .exception to get the stack trace, and reconnect
                    logger.exception(f"Unknown exception. Will retry - {e}")

    async def process_message(self, msg):
        with tracer.start_as_current_span("process_message") as current_span:
            complete_message = False

            try:
                message = parse_obj_as(StepResultStatusUpdateMessage, json.loads(str(msg)))

                current_span.set_attribute("step_id", message.id)
                current_span.set_attribute("event_type", message.eventType)
                current_span.set_attribute("topic", message.topic)

                logger.info(f"Received step_result status update message with correlation ID {message.id}: {message}")
                complete_message = await self.update_status_in_database(message)
                logger.info(f"Update status in DB for {message.id}")
            except (json.JSONDecodeError, ValidationError):
                logger.exception(f"{strings.STEP_RESULT_MESSAGE_FORMAT_INCORRECT}: {msg.correlation_id}")
                complete_message = True
            except Exception:
                logger.exception(f"Exception processing message: {msg.correlation_id}")

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
                logger.error(strings.STEP_RESULT_MESSAGE_STATUS_DOES_NOT_MATCH.format(airlock_request_id, current_status, airlock_request.status))
        except HTTPException as e:
            if e.status_code == 404:
                # Marking as true as this message will never succeed anyways and should be removed from the queue.
                result = True
                logger.exception(strings.STEP_RESULT_ID_NOT_FOUND.format(airlock_request_id))
            if e.status_code == 400:
                result = True
                logger.exception(strings.STEP_RESULT_MESSAGE_INVALID_STATUS.format(airlock_request_id, current_status, new_status))
            if e.status_code == 503:
                logger.exception(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
        except Exception:
            logger.exception("Failed updating request status")

        return result
