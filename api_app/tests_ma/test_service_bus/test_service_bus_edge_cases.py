import asyncio
import time
import pytest
from unittest.mock import patch
from service_bus.service_bus_consumer import (
    ServiceBusConsumer,
    RESTART_DELAY_SECONDS,
    HEARTBEAT_CHECK_INTERVAL_SECONDS,
    HEARTBEAT_STALENESS_THRESHOLD_SECONDS,
    MAX_RESTART_DELAY_SECONDS,
    SUPERVISOR_ERROR_DELAY_SECONDS,
)


# Create a concrete implementation for testing edge cases
class MockConsumerForEdgeCases(ServiceBusConsumer):
    def __init__(self):
        super().__init__("test_consumer_edge")
        self.receive_messages_called = False

    async def receive_messages(self):
        self.receive_messages_called = True
        await asyncio.sleep(0.01)
        return


@pytest.mark.asyncio
async def test_supervisor_error_recovery():
    """Test supervisor recovers from an unexpected error in the main loop."""
    consumer = MockConsumerForEdgeCases()

    error_triggered = False
    iteration = 0

    class MockTask:
        def done(self):
            return False

        def cancel(self):
            pass

        def __await__(self):
            async def _await():
                return None
            return _await().__await__()

    async def mock_sleep(duration):
        nonlocal iteration, error_triggered
        iteration += 1
        if iteration == 1 and not error_triggered:
            error_triggered = True
            raise ValueError("Unexpected supervisor error")
        if iteration >= 3:
            raise KeyboardInterrupt("Test complete")

    def create_mock_task(coro):
        coro.close()
        return MockTask()

    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.asyncio.create_task", side_effect=create_mock_task):
        try:
            await consumer.supervisor_with_heartbeat_check()
        except KeyboardInterrupt:
            pass

    assert error_triggered, "Supervisor should have encountered and recovered from the error"


@pytest.mark.asyncio
async def test_supervisor_backoff_not_reset_on_stale_heartbeat():
    """Test that backoff is NOT reset when restarting due to stale heartbeat.
    Backoff only resets after a healthy heartbeat cycle."""
    consumer = MockConsumerForEdgeCases()
    consumer._restart_delay = 160

    heartbeat_calls = 0

    def mock_check_heartbeat(**kwargs):
        nonlocal heartbeat_calls
        heartbeat_calls += 1
        if heartbeat_calls == 1:
            return False  # Stale — backoff should NOT reset
        raise KeyboardInterrupt("Test complete")

    async def mock_sleep(duration):
        pass

    class MockTask:
        def done(self):
            return False

        def cancel(self):
            pass

        def __await__(self):
            async def _await():
                return None
            return _await().__await__()

    consumer.check_heartbeat = mock_check_heartbeat

    def create_mock_task(coro):
        coro.close()
        return MockTask()

    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.asyncio.create_task", side_effect=create_mock_task):
        try:
            await consumer.supervisor_with_heartbeat_check()
        except KeyboardInterrupt:
            pass

    # Backoff is preserved after stale heartbeat restart (not reset until a healthy cycle)
    assert consumer._restart_delay == 160
