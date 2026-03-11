import asyncio
import time

from services.logging import logger

# Configuration constants for monitoring intervals
HEARTBEAT_CHECK_INTERVAL_SECONDS = 60
HEARTBEAT_STALENESS_THRESHOLD_SECONDS = 300
RESTART_DELAY_SECONDS = 5
MAX_RESTART_DELAY_SECONDS = 300
SUPERVISOR_ERROR_DELAY_SECONDS = 30


class ServiceBusConsumer:

    def __init__(self, consumer_name: str):
        self.service_name = consumer_name.replace('_', ' ').title()
        self._last_heartbeat: float = time.monotonic()
        self._restart_delay: float = RESTART_DELAY_SECONDS
        logger.info(f"Initializing {self.service_name}")

    def update_heartbeat(self):
        self._last_heartbeat = time.monotonic()

    def check_heartbeat(self, max_age_seconds: int = HEARTBEAT_STALENESS_THRESHOLD_SECONDS) -> bool:
        age = time.monotonic() - self._last_heartbeat
        if age > max_age_seconds:
            logger.warning(f"{self.service_name} heartbeat is {age:.1f}s old (threshold: {max_age_seconds}s)")
            return False
        return True

    async def supervisor_with_heartbeat_check(self):
        task = None
        try:
            while True:
                try:
                    task_just_started = False
                    if task is None or task.done():
                        if task and task.done():
                            try:
                                await task
                            except Exception as e:
                                logger.exception(f"{self.service_name} task failed: {e}")
                            await asyncio.sleep(self._restart_delay)
                            self._restart_delay = min(self._restart_delay * 2, MAX_RESTART_DELAY_SECONDS)

                        logger.info(f"Starting {self.service_name} task...")
                        task = asyncio.create_task(self.receive_messages())
                        self.update_heartbeat()
                        task_just_started = True

                    await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL_SECONDS)

                    if not self.check_heartbeat():
                        logger.warning(f"{self.service_name} heartbeat stale, restarting...")
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        task = None
                    elif not task_just_started:
                        self._restart_delay = RESTART_DELAY_SECONDS
                except Exception as e:
                    logger.exception(f"{self.service_name} supervisor error: {e}")
                    await asyncio.sleep(SUPERVISOR_ERROR_DELAY_SECONDS)
        finally:
            if task and not task.done():
                logger.info(f"Cleaning up {self.service_name} task...")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def receive_messages(self):
        raise NotImplementedError("Subclasses must implement receive_messages()")
