import asyncio
import time
import pytest
from unittest.mock import patch

from service_bus.service_bus_consumer import (
    ServiceBusConsumer,
    HEARTBEAT_STALENESS_THRESHOLD_SECONDS,
    RESTART_DELAY_SECONDS,
    MAX_RESTART_DELAY_SECONDS,
)


# Create a concrete implementation for testing
class MockConsumer(ServiceBusConsumer):
    def __init__(self):
        super().__init__("test_consumer")
        self.receive_messages_called = False

    async def receive_messages(self):
        self.receive_messages_called = True
        await asyncio.sleep(0.1)
        return


@pytest.mark.asyncio
async def test_init():
    """Test initialization of ServiceBusConsumer."""
    consumer = MockConsumer()
    assert consumer.service_name == "Test Consumer"
    assert consumer._restart_delay == RESTART_DELAY_SECONDS
    assert consumer._last_heartbeat > 0


@pytest.mark.asyncio
async def test_update_heartbeat():
    """Test updating heartbeat updates timestamp."""
    consumer = MockConsumer()
    old_heartbeat = consumer._last_heartbeat
    await asyncio.sleep(0.01)
    consumer.update_heartbeat()

    assert consumer._last_heartbeat > old_heartbeat


@pytest.mark.asyncio
async def test_check_heartbeat_recent():
    """Test checking a recent heartbeat returns True."""
    consumer = MockConsumer()
    assert consumer.check_heartbeat(max_age_seconds=300) is True


@pytest.mark.asyncio
async def test_check_heartbeat_stale():
    """Test checking a stale heartbeat returns False."""
    consumer = MockConsumer()
    consumer._last_heartbeat = time.monotonic() - 400
    assert consumer.check_heartbeat(max_age_seconds=300) is False


@pytest.mark.asyncio
async def test_check_heartbeat_default_uses_constant():
    """Test that check_heartbeat default max_age_seconds uses the module constant."""
    import inspect
    sig = inspect.signature(ServiceBusConsumer.check_heartbeat)
    default = sig.parameters['max_age_seconds'].default
    assert default == HEARTBEAT_STALENESS_THRESHOLD_SECONDS


@pytest.mark.asyncio
async def test_backoff_increases_on_consecutive_failures():
    """Test that restart delay increases exponentially on immediate failures."""
    consumer = MockConsumer()

    async def failing_receive():
        raise RuntimeError("Simulated failure")

    consumer.receive_messages = failing_receive

    sleep_calls = []
    call_count = 0

    async def mock_sleep(duration):
        nonlocal call_count
        sleep_calls.append(duration)
        call_count += 1
        if call_count >= 3:
            raise asyncio.CancelledError()

    # Patch time.monotonic to always return the same value so elapsed time is 0 (immediate failure)
    fixed_time = time.monotonic()
    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.time.monotonic", return_value=fixed_time):
        try:
            await consumer._receive_messages_loop()
        except asyncio.CancelledError:
            pass

    assert sleep_calls[0] == RESTART_DELAY_SECONDS
    assert sleep_calls[1] == RESTART_DELAY_SECONDS * 2
    assert sleep_calls[2] == RESTART_DELAY_SECONDS * 4


@pytest.mark.asyncio
async def test_backoff_caps_at_maximum():
    """Test that restart delay caps at MAX_RESTART_DELAY_SECONDS."""
    consumer = MockConsumer()
    consumer._restart_delay = MAX_RESTART_DELAY_SECONDS

    async def failing_receive():
        raise RuntimeError("Simulated failure")

    consumer.receive_messages = failing_receive

    sleep_calls = []

    async def mock_sleep(duration):
        sleep_calls.append(duration)
        raise asyncio.CancelledError()

    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep):
        try:
            await consumer._receive_messages_loop()
        except asyncio.CancelledError:
            pass

    assert sleep_calls[0] == MAX_RESTART_DELAY_SECONDS


@pytest.mark.asyncio
async def test_supervisor_restarts_failed_task():
    """Test supervisor restarts the receive_messages task when it fails."""
    consumer = MockConsumer()

    task_create_calls = 0
    sleep_calls = []

    class FailOnFirstDoneTask:
        """A mock task that reports done() immediately to simulate task failure."""

        def __init__(self):
            nonlocal task_create_calls
            task_create_calls += 1
            self._is_first_task = (task_create_calls == 1)

        def done(self):
            # First task always reports done (crashed)
            # Second task always reports running
            return self._is_first_task

        def cancel(self):
            pass

        def __await__(self):
            async def _await():
                if self._is_first_task:
                    raise RuntimeError("Simulated task failure")
                return None
            return _await().__await__()

    iteration = 0

    async def mock_sleep(duration):
        nonlocal iteration
        sleep_calls.append(duration)
        iteration += 1
        if iteration >= 4:
            raise KeyboardInterrupt("Test complete")

    consumer.check_heartbeat = lambda **kwargs: True

    def create_fail_task(coro):
        coro.close()
        return FailOnFirstDoneTask()

    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.asyncio.create_task", side_effect=create_fail_task):
        try:
            await consumer.supervisor_with_heartbeat_check()
        except KeyboardInterrupt:
            pass

    assert task_create_calls >= 2


@pytest.mark.asyncio
async def test_supervisor_restarts_on_stale_heartbeat():
    """Test supervisor cancels and restarts task when heartbeat goes stale."""
    consumer = MockConsumer()

    heartbeat_calls = 0
    task_create_calls = 0
    task_cancel_calls = 0
    sleep_calls = []

    def mock_check_heartbeat(**kwargs):
        nonlocal heartbeat_calls
        heartbeat_calls += 1
        if heartbeat_calls == 1:
            return True  # Heartbeat is fresh
        elif heartbeat_calls == 2:
            return False  # Heartbeat is stale, should trigger restart
        else:
            raise KeyboardInterrupt("Test complete")

    async def mock_sleep(duration):
        sleep_calls.append(duration)

    class MockTask:
        def __init__(self):
            nonlocal task_create_calls
            task_create_calls += 1

        def cancel(self):
            nonlocal task_cancel_calls
            task_cancel_calls += 1

        def done(self):
            return False

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

    assert heartbeat_calls >= 2
    assert task_create_calls >= 2
    assert task_cancel_calls >= 1
    assert 60 in sleep_calls
    assert consumer._restart_delay == RESTART_DELAY_SECONDS
