import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from shared.logging import logger

RETRY_SECONDS = 5


async def stop(task: asyncio.Task) -> None:
    """Cancel a renewal task and wait for it, without hiding a cancellation of the caller."""
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        current = asyncio.current_task()
        if current is not None and current.cancelling():
            raise


def seconds_until(moment: Optional[datetime]) -> float:
    return (moment - datetime.now(timezone.utc)).total_seconds() if moment else 0


async def keep_renewed(
    name: str,
    renew: Callable[[], Awaitable[object]],
    seconds_left: Callable[[], float],
    describe: Callable[[], str],
    *,
    interval: float,
    retry_seconds: float = RETRY_SECONDS,
    paused: Callable[[], bool] = lambda: False,
) -> None:
    """Renew a lock until the caller cancels this task.

    AutoLockRenewer stops after one failed renewal and logs it only at debug level.
    This task tries again until the lock expires, and logs each failure.
    """
    while True:
        await asyncio.sleep(interval)
        if paused():
            continue
        attempt = 0
        while True:
            try:
                await renew()
                break
            except asyncio.CancelledError:
                raise
            except Exception as error:
                attempt += 1
                remaining = seconds_left()
                if remaining <= 0:
                    # Another worker can now get the lock and run the same step.
                    logger.error(f"{name} expired after {attempt} failed renewals for {describe()}: {error!r}")
                    return
                logger.warning(f"{name} renewal {attempt} failed for {describe()}: {error!r}")
                await asyncio.sleep(min(retry_seconds * attempt, remaining))
