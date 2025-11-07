import asyncio
import os
import tempfile
import time

from services.logging import logger

# Configuration constants for monitoring intervals
HEARTBEAT_CHECK_INTERVAL_SECONDS = 60
HEARTBEAT_STALENESS_THRESHOLD_SECONDS = 300
RESTART_DELAY_SECONDS = 5
SUPERVISOR_ERROR_DELAY_SECONDS = 30


class ServiceBusConsumer:

    def __init__(self, heartbeat_file_prefix: str):
        # Create a unique identifier for this worker process
        self.worker_id = os.getpid()
        temp_dir = tempfile.gettempdir()
        self.heartbeat_file = os.path.join(temp_dir, f"{heartbeat_file_prefix}_heartbeat_{self.worker_id}.txt")
        self.service_name = heartbeat_file_prefix.replace('_', ' ').title()
        logger.info(f"Initializing {self.service_name}")

    def update_heartbeat(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.heartbeat_file), exist_ok=True)
            with open(self.heartbeat_file, 'w') as f:
                f.write(str(time.time()))
        except PermissionError:
            logger.error(f"Permission denied writing heartbeat to {self.heartbeat_file}")
        except OSError as e:
            logger.error(f"OS error updating heartbeat: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error updating heartbeat: {e}")

    def check_heartbeat(self, max_age_seconds: int = 300) -> bool:
        try:
            if not os.path.exists(self.heartbeat_file):
                logger.warning("Heartbeat file does not exist")
                return False

            with open(self.heartbeat_file, 'r') as f:
                heartbeat_time = float(f.read().strip())

            current_time = time.time()
            age = current_time - heartbeat_time

            if age > max_age_seconds:
                logger.warning(f"Heartbeat is {age:.1f} seconds old, exceeding the limit of {max_age_seconds} seconds")

            return age <= max_age_seconds
        except (ValueError, IOError) as e:
            logger.warning(f"Failed to read heartbeat: {e}")
            return False

    async def receive_messages_with_restart_check(self):
        while True:
            try:
                logger.info("Starting the receive_messages loop...")
                await self.receive_messages()
            except Exception as e:
                logger.exception(f"receive_messages stopped unexpectedly. Restarting... - {e}")
                await asyncio.sleep(RESTART_DELAY_SECONDS)

    async def supervisor_with_heartbeat_check(self):
        task = None
        try:
            while True:
                try:
                    # Start the receive_messages task if not running
                    if task is None or task.done():
                        if task and task.done():
                            try:
                                await task  # Check for any exception
                            except Exception as e:
                                logger.exception(f"receive_messages task failed: {e}")

                        logger.info("Starting receive_messages task...")
                        task = asyncio.create_task(self.receive_messages_with_restart_check())

                    # Wait before checking heartbeat
                    await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL_SECONDS)  # Check every minute

                    # Check if heartbeat is stale
                    if not self.check_heartbeat(max_age_seconds=HEARTBEAT_STALENESS_THRESHOLD_SECONDS):  # 5 minutes max age
                        logger.warning("Heartbeat is stale, restarting receive_messages task...")
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            # Expected when cancelling a task - ignore and proceed with restart
                            pass
                        task = None
                except Exception as e:
                    logger.exception(f"Supervisor error: {e}")
                    await asyncio.sleep(SUPERVISOR_ERROR_DELAY_SECONDS)
        finally:
            # Ensure proper cleanup on shutdown
            if task and not task.done():
                logger.info("Cleaning up supervisor task...")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def receive_messages(self):
        raise NotImplementedError("Subclasses must implement receive_messages()")
