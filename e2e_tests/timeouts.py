"""Cooperative deadlines for asynchronous test bodies."""

import asyncio
from functools import wraps


def async_test_timeout(seconds):
    """Finish cancellation before pytest starts another test or fixture cleanup."""

    def decorate(test):
        @wraps(test)
        async def bounded_test(*args, **kwargs):
            async with asyncio.timeout(seconds):
                return await test(*args, **kwargs)

        return bounded_test

    return decorate
