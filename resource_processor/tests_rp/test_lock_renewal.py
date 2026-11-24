import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from helpers import lock_renewal


async def run_until(task_condition, coroutine):
    task = asyncio.create_task(coroutine)
    for _ in range(200):
        await asyncio.sleep(0)
        if task_condition() or task.done():
            break
    if not task.done():
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    return task


@pytest.mark.asyncio
async def test_renews_at_each_interval():
    renew = AsyncMock()
    task = await run_until(
        lambda: renew.await_count >= 3,
        lock_renewal.keep_renewed("Session lock", renew, lambda: 300, lambda: "step", interval=0),
    )
    assert renew.await_count >= 3
    assert task.cancelled()


@pytest.mark.asyncio
async def test_a_failed_renewal_is_tried_again_and_logged():
    renew = AsyncMock(side_effect=[RuntimeError("busy"), None, None])
    with patch.object(lock_renewal, "logger") as logger:
        await run_until(
            lambda: renew.await_count >= 3,
            lock_renewal.keep_renewed(
                "Session lock", renew, lambda: 300, lambda: "step 1", interval=0, retry_seconds=0
            ),
        )
    logger.warning.assert_called_once()
    assert "Session lock renewal 1 failed for step 1" in logger.warning.call_args.args[0]
    logger.error.assert_not_called()


@pytest.mark.asyncio
async def test_an_expired_lock_is_logged_as_an_error_and_ends_the_task():
    renew = AsyncMock(side_effect=RuntimeError("lock lost"))
    with patch.object(lock_renewal, "logger") as logger:
        await lock_renewal.keep_renewed("Execution lease", renew, lambda: 0, lambda: "step 2", interval=0)
    renew.assert_awaited_once()
    assert "Execution lease expired after 1 failed renewals for step 2" in logger.error.call_args.args[0]


@pytest.mark.asyncio
async def test_a_paused_renewal_does_not_renew():
    renew = AsyncMock()
    checks = []

    def paused():
        checks.append(True)
        return True

    await run_until(
        lambda: len(checks) >= 3,
        lock_renewal.keep_renewed("Session lock", renew, lambda: 300, lambda: "step", interval=0, paused=paused),
    )
    renew.assert_not_awaited()


def test_seconds_until_without_a_time_is_zero():
    assert lock_renewal.seconds_until(None) == 0


@pytest.mark.asyncio
async def test_stop_ends_the_renewal_and_returns():
    renewal = asyncio.create_task(asyncio.Event().wait())
    await asyncio.sleep(0)
    await lock_renewal.stop(renewal)
    assert renewal.cancelled()


@pytest.mark.asyncio
async def test_stop_keeps_a_cancellation_of_the_caller():
    in_stop = asyncio.Event()

    async def slow_renewal():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            in_stop.set()
            await asyncio.sleep(0.2)
            raise

    async def caller():
        renewal = asyncio.create_task(slow_renewal())
        await asyncio.sleep(0)
        await lock_renewal.stop(renewal)
        return "finished"

    task = asyncio.create_task(caller())
    await in_stop.wait()
    # The caller is cancelled while it waits for the renewal task to end.
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
