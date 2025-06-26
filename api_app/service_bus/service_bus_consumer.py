import asyncio
import os
import time

from services.logging import logger


class ServiceBusConsumer:

    def __init__(self, heartbeat_file_prefix: str):
        # Create a unique identifier for this worker process
        import tempfile
        self.worker_id = os.getpid()
        temp_dir = tempfile.gettempdir()
        self.heartbeat_file = os.path.join(temp_dir, f"{heartbeat_file_prefix}_heartbeat_{self.worker_id}.txt")
        self.service_name = heartbeat_file_prefix.replace('_', ' ').title()
        logger.info(f"Initializing {self.service_name}")

    def update_heartbeat(self):
        try:
            with open(self.heartbeat_file, 'w') as f:
                f.write(str(time.time()))
        except Exception as e:
            logger.warning(f"Failed to update heartbeat: {e}")

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
                await asyncio.sleep(5)

    async def supervisor_with_heartbeat_check(self):
        task = None
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
                    task = asyncio.create_task(self.receive_messages())

                # Wait before checking heartbeat
                await asyncio.sleep(60)  # Check every minute

                # Check if heartbeat is stale
                if not self.check_heartbeat(max_age_seconds=300):  # 5 minutes max age
                    logger.warning("Heartbeat is stale, restarting receive_messages task...")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    task = None
            except Exception as e:
                logger.exception(f"Supervisor error: {e}")
                await asyncio.sleep(30)

    async def receive_messages(self):
        raise NotImplementedError("Subclasses must implement receive_messages()")
