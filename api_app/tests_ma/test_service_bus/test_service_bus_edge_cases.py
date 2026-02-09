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
async def test_stale_heartbeat_detection():
    """Test that stale heartbeat is correctly detected."""
    consumer = MockConsumerForEdgeCases()
    consumer._last_heartbeat = time.monotonic() - 400
    assert consumer.check_heartbeat(max_age_seconds=300) is False


@pytest.mark.asyncio
async def test_fresh_heartbeat_detection():
    """Test that fresh heartbeat is correctly detected."""
    consumer = MockConsumerForEdgeCases()
    assert consumer.check_heartbeat(max_age_seconds=300) is True


@pytest.mark.asyncio
async def test_backoff_resets_after_long_running_receive():
    """Test that backoff resets when receive_messages ran longer than the current delay."""
    consumer = MockConsumerForEdgeCases()
    consumer._restart_delay = 80

    monotonic_values = iter([100.0, 200.0, 200.0])  # start=100, elapsed_check=200 (ran 100s > 80s delay), then next start

    async def long_running_receive():
        raise RuntimeError("Failure after running a while")

    consumer.receive_messages = long_running_receive

    async def mock_sleep(duration):
        raise asyncio.CancelledError()

    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.time.monotonic", side_effect=monotonic_values):
        try:
            await consumer._receive_messages_loop()
        except asyncio.CancelledError:
            pass

    # Backoff should have reset to base since elapsed (100s) > old delay (80s)
    assert consumer._restart_delay == RESTART_DELAY_SECONDS


@pytest.mark.asyncio
async def test_supervisor_cleanup_on_exception():
    """Test supervisor properly cleans up tasks when interrupted."""
    consumer = MockConsumerForEdgeCases()

    # Track task lifecycle
    task_created = False
    task_cancelled = False

    class MockTask:
        def __init__(self):
            nonlocal task_created
            task_created = True
            self.done_count = 0

        def done(self):
            return self.done_count > 0

        def cancel(self):
            nonlocal task_cancelled
            task_cancelled = True
            self.done_count = 1

        def __await__(self):
            async def _await():
                if task_cancelled:
                    raise asyncio.CancelledError()
                return None
            return _await().__await__()

    # Mock to trigger cleanup after one iteration
    call_count = 0

    async def mock_sleep(duration):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:  # Trigger cleanup after heartbeat check
            raise KeyboardInterrupt("Test cleanup")

    def create_mock_task(coro):
        # Close the coroutine to avoid "coroutine never awaited" warning
        coro.close()
        return MockTask()

    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.asyncio.create_task", side_effect=create_mock_task), \
            patch.object(consumer, "check_heartbeat", return_value=True):

        try:
            await consumer.supervisor_with_heartbeat_check()
        except KeyboardInterrupt:
            # Intentionally ignore KeyboardInterrupt to test cleanup logic after interruption
            pass

    # Verify task was created and cancelled during cleanup
    assert task_created, "Task should have been created"
    assert task_cancelled, "Task should have been cancelled during cleanup"


def test_restart_delay_configuration():
    """Test that configuration constants exist and have reasonable values."""
    assert RESTART_DELAY_SECONDS > 0
    assert RESTART_DELAY_SECONDS <= 10
    assert MAX_RESTART_DELAY_SECONDS >= RESTART_DELAY_SECONDS
    assert MAX_RESTART_DELAY_SECONDS <= 600
    assert HEARTBEAT_CHECK_INTERVAL_SECONDS > 0
    assert HEARTBEAT_STALENESS_THRESHOLD_SECONDS > HEARTBEAT_CHECK_INTERVAL_SECONDS
    assert SUPERVISOR_ERROR_DELAY_SECONDS > 0


@pytest.mark.asyncio
async def test_supervisor_resets_backoff_on_stale_heartbeat_restart():
    """Test that supervisor resets backoff when restarting due to stale heartbeat."""
    consumer = MockConsumerForEdgeCases()
    consumer._restart_delay = 160

    heartbeat_calls = 0

    def mock_check_heartbeat(**kwargs):
        nonlocal heartbeat_calls
        heartbeat_calls += 1
        if heartbeat_calls == 1:
            return False
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

    assert consumer._restart_delay == RESTART_DELAY_SECONDS
