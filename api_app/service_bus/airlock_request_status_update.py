import asyncio
import json
import time

from azure.servicebus.aio import ServiceBusClient, AutoLockRenewer
from azure.servicebus.exceptions import OperationTimeoutError, ServiceBusConnectionError
from fastapi import HTTPException
from pydantic import ValidationError, TypeAdapter

from api.dependencies.airlock import get_airlock_request_by_id
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
                    async with credentials.get_credential_async_context() as credential:
                        async with ServiceBusClient(config.SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE, credential) as service_bus_client:
                            client_created_time = time.time()
                            while True:
                                try:
                                    if time.time() - client_created_time > 3600:
                                        logger.info("ServiceBusClient has been active for 1 hour. Recreating for freshness...")
                                        break

                                    current_time = time.time()
                                    polling_count += 1
                                    if current_time - last_heartbeat_time >= 60:
                                        logger.info(f"Queue reader heartbeat: Polled {config.SERVICE_BUS_STEP_RESULT_QUEUE} queue {polling_count} times in the last minute")
                                        last_heartbeat_time = current_time
                                        polling_count = 0

                                    logger.debug(f"Looking for new messages on {config.SERVICE_BUS_STEP_RESULT_QUEUE} queue...")
                                    receiver = service_bus_client.get_queue_receiver(queue_name=config.SERVICE_BUS_STEP_RESULT_QUEUE)
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
                                    # Timeout occurred whilst connecting - this is expected and indicates no messages are available
                                    logger.debug("No messages for this process. Will look again...")

                except ServiceBusConnectionError:
                    # Occasionally there will be a transient / network-level error in connecting to SB.
                    logger.info("Unknown Service Bus connection error. Will retry...")
                    await asyncio.sleep(10)

                except asyncio.CancelledError:
                    raise

                except Exception as e:
                    logger.exception(f"Unknown exception. Will retry - {e}")
                    await asyncio.sleep(10)

    async def process_message(self, msg):
        with tracer.start_as_current_span("process_message") as current_span:
            complete_message = False

            try:
                message = TypeAdapter(StepResultStatusUpdateMessage).validate_python(json.loads(str(msg)))

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

    async def _complete_submission_if_ready(self, airlock_request):
        """A submitted request advances only once file validation and the scan verdict are both in."""
        if airlock_request.status != AirlockRequestStatus.Submitted:
            return
        if not airlock_request.files or airlock_request.scanResult is None:
            return

        clean = airlock_request.scanResult.get("clean")
        if clean is True:
            new_status, status_message = AirlockRequestStatus.InReview, None
        elif clean is False:
            new_status, status_message = AirlockRequestStatus.BlockingInProgress, airlock_request.scanResult.get("message")
        else:
            # A malformed verdict must never be read as clean, so leave the request where it is.
            logger.error(f"Request {airlock_request.id} has a malformed scan verdict, not advancing: {airlock_request.scanResult}")
            return

        logger.info(f"Completing submission for request {airlock_request.id} with status '{new_status}'.")
        workspace = await self.workspace_repo.get_workspace_by_id(airlock_request.workspaceId)
        await update_and_publish_event_airlock_request(
            airlock_request=airlock_request, airlock_request_repo=self.airlock_request_repo,
            updated_by=airlock_request.updatedBy, workspace=workspace,
            new_status=new_status, status_message=status_message)

    async def update_status_in_database(self, step_result_message: StepResultStatusUpdateMessage):
        """
        Updates an airlock request and with the new status from step_result message contents.

        """
        result = False
        try:
            step_result_data = step_result_message.data
            airlock_request_id = step_result_data.request_id
            completed_step = step_result_data.completed_step
            new_status = AirlockRequestStatus(step_result_data.new_status) if step_result_data.new_status else None
            status_message = step_result_data.status_message
            request_files = step_result_data.request_files
            scan_result = step_result_data.scan_result
            # Find the airlock request by id
            airlock_request = await get_airlock_request_by_id(airlock_request_id=airlock_request_id, airlock_request_repo=self.airlock_request_repo)
            if airlock_request.status in AirlockRequestRepository.FINAL_AIRLOCK_STATUSES:
                logger.info(f"Discarding step result for request {airlock_request_id} in final status '{airlock_request.status}'.")
                return True

            # File enumeration is a fact about the data and can arrive after the transition it
            # accompanied, so record it regardless of the current status rather than discarding it.
            if request_files and not airlock_request.files:
                airlock_request = await self.airlock_request_repo.update_airlock_request(
                    original_request=airlock_request,
                    updated_by=airlock_request.updatedBy,
                    request_files=request_files)
                result = True

            if scan_result is not None:
                # A verdict is a fact about the data, so it is recorded in any non-final status.
                airlock_request = await self.airlock_request_repo.update_airlock_request(
                    original_request=airlock_request,
                    updated_by=airlock_request.updatedBy,
                    scan_result=scan_result)
                result = True
            elif new_status is None:
                # A file-only result carries no transition; the facts above are enough. Acknowledge it
                # without republishing, which previously risked a submitted -> submitted event loop.
                result = True
            elif airlock_request.status == completed_step:
                workspace = await self.workspace_repo.get_workspace_by_id(airlock_request.workspaceId)
                # update to new status and send to event grid
                airlock_request = await update_and_publish_event_airlock_request(airlock_request=airlock_request, airlock_request_repo=self.airlock_request_repo, updated_by=airlock_request.updatedBy, workspace=workspace, new_status=new_status, request_files=request_files, status_message=status_message)
                result = True
            elif airlock_request.status == new_status:
                # Redelivery of a result that was already applied. Retrying forever would dead-letter a valid message.
                logger.info(f"Step result for request {airlock_request_id} already applied, acknowledging duplicate.")
                return True
            else:
                logger.error(strings.STEP_RESULT_MESSAGE_STATUS_DOES_NOT_MATCH.format(airlock_request_id, completed_step, airlock_request.status))
                return result

            await self._complete_submission_if_ready(airlock_request)

        except HTTPException as e:
            if e.status_code == 404:
                # Marking as true as this message will never succeed anyways and should be removed from the queue.
                result = True
                logger.exception(strings.STEP_RESULT_ID_NOT_FOUND.format(airlock_request_id))
            if e.status_code == 400:
                result = True
                logger.exception(strings.STEP_RESULT_MESSAGE_INVALID_STATUS.format(airlock_request_id, completed_step, new_status))
            if e.status_code == 503:
                logger.exception(strings.STATE_STORE_ENDPOINT_NOT_RESPONDING)
        except Exception:
            logger.exception("Failed updating request status")

        return result
