"""Cooperative deadlines for asynchronous test bodies."""

import asyncio
from functools import wraps
from contextlib import asynccontextmanager
from contextvars import ContextVar


def async_test_timeout(seconds):
    """Finish cancellation before pytest starts another test or fixture cleanup."""

    def decorate(test):
        @wraps(test)
        async def bounded_test(*args, **kwargs):
            async with asyncio.timeout(seconds):
                return await test(*args, **kwargs)

        return bounded_test

    return decorate


_CLEANUP_DEADLINE = ContextVar("e2e_cleanup_deadline", default=None)


@asynccontextmanager
async def cleanup_deadline(seconds):
    """Share one absolute deadline across nested resource finalisers."""
    loop = asyncio.get_running_loop()
    outer = _CLEANUP_DEADLINE.get()
    deadline = min(outer, loop.time() + seconds) if outer is not None else loop.time() + seconds
    if loop.time() >= deadline:
        raise TimeoutError("The shared resource cleanup deadline has expired")
    token = _CLEANUP_DEADLINE.set(deadline)
    timeout = asyncio.timeout_at(deadline)
    try:
        async with timeout:
            yield timeout
    finally:
        _CLEANUP_DEADLINE.reset(token)
