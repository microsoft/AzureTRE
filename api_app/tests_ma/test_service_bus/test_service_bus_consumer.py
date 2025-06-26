import asyncio
import pytest
from unittest.mock import patch

from service_bus.service_bus_consumer import ServiceBusConsumer


# Create a concrete implementation for testing
class MockConsumer(ServiceBusConsumer):
    def __init__(self):
        super().__init__("test_consumer")
        self.receive_messages_called = False

    async def receive_messages(self):
        self.receive_messages_called = True
        # Simulate running once and then exiting
        await asyncio.sleep(0.1)
        return


@pytest.mark.asyncio
@patch("service_bus.service_bus_consumer.os.getpid", return_value=12345)
async def test_init(mock_getpid):
    """Test initialization of ServiceBusConsumer."""
    consumer = MockConsumer()
    assert consumer.worker_id == 12345
    assert consumer.heartbeat_file == "/tmp/test_consumer_heartbeat_12345.txt"
    assert consumer.service_name == "Test Consumer"


@pytest.mark.asyncio
@patch("service_bus.service_bus_consumer.os.path.exists", return_value=True)
@patch("builtins.open", create=True)
async def test_check_heartbeat_recent(mock_open, mock_exists):
    """Test checking a recent heartbeat."""
    mock_open.return_value.__enter__.return_value.read.return_value = "1234567890.0"

    with patch("service_bus.service_bus_consumer.time.time", return_value=1234567890.0 + 60):  # 60 seconds later
        consumer = MockConsumer()
        result = consumer.check_heartbeat(max_age_seconds=300)
        assert result is True


@pytest.mark.asyncio
@patch("service_bus.service_bus_consumer.os.path.exists", return_value=True)
@patch("builtins.open", create=True)
async def test_check_heartbeat_stale(mock_open, mock_exists):
    """Test checking a stale heartbeat."""
    mock_open.return_value.__enter__.return_value.read.return_value = "1234567890.0"

    with patch("service_bus.service_bus_consumer.time.time", return_value=1234567890.0 + 400):  # 400 seconds later
        consumer = MockConsumer()
        result = consumer.check_heartbeat(max_age_seconds=300)
        assert result is False


@pytest.mark.asyncio
@patch("service_bus.service_bus_consumer.os.getpid", return_value=12345)
@patch("service_bus.service_bus_consumer.time.time", return_value=1234567890.0)
@patch("builtins.open", create=True)
async def test_update_heartbeat(mock_open, mock_time, mock_getpid):
    """Test updating heartbeat."""
    consumer = MockConsumer()
    consumer.update_heartbeat()

    import tempfile
    expected_path = f"{tempfile.gettempdir()}/test_consumer_heartbeat_12345.txt"
    mock_open.assert_called_once_with(expected_path, 'w')
    mock_open.return_value.__enter__.return_value.write.assert_called_once_with("1234567890.0")


@pytest.mark.asyncio
async def test_receive_messages_with_restart_check():
    """Test receive_messages_with_restart_check calls receive_messages and handles exceptions."""
    consumer = MockConsumer()

    # Track how many times receive_messages has been called
    receive_messages_call_count = 0
    sleep_calls = []

    async def mock_receive_messages():
        nonlocal receive_messages_call_count
        receive_messages_call_count += 1
        if receive_messages_call_count == 1:
            # First call raises an exception
            raise Exception("Test exception")
        elif receive_messages_call_count == 2:
            # Second call succeeds, but we need to break the infinite loop
            # Let's raise a special exception to break out
            raise KeyboardInterrupt("Break out of loop for test")
        else:
            # Should not get here in this test
            return

    async def mock_sleep(duration):
        sleep_calls.append(duration)
        # Just return immediately instead of sleeping
        return

    # Override the method with our mock
    consumer.receive_messages = mock_receive_messages

    # Patch asyncio.sleep in the service_bus_consumer module
    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep):
        try:
            # Run the method, expecting it to call receive_messages twice and then break
            await consumer.receive_messages_with_restart_check()
        except KeyboardInterrupt:
            # This is our expected way out of the infinite loop
            pass

    # Verify that receive_messages was called twice and sleep was called once
    assert receive_messages_call_count == 2, f"Expected exactly 2 calls to receive_messages, got {receive_messages_call_count}"
    assert len(sleep_calls) == 1, f"Expected exactly 1 sleep call for restart delay, got {len(sleep_calls)}"
    assert sleep_calls[0] == 5, f"Expected sleep(5) call for restart delay, got {sleep_calls}"


@pytest.mark.asyncio
async def test_supervisor_with_heartbeat_check():
    """Test supervisor_with_heartbeat_check manages the receive_messages task."""
    consumer = MockConsumer()

    # Track method calls and task lifecycle
    heartbeat_calls = 0
    task_create_calls = 0
    task_cancel_calls = 0
    sleep_calls = []

    # Mock check_heartbeat to return False on second call (to trigger restart)
    def mock_check_heartbeat(max_age_seconds=300):
        nonlocal heartbeat_calls
        heartbeat_calls += 1
        # Return True first, then False to trigger restart, then break the loop
        if heartbeat_calls == 1:
            return True  # Heartbeat is fresh
        elif heartbeat_calls == 2:
            return False  # Heartbeat is stale, should trigger restart
        else:
            # Break out of the infinite loop after testing restart logic
            raise KeyboardInterrupt("Test complete")

    # Track sleep calls
    async def mock_sleep(duration):
        sleep_calls.append(duration)
        # Don't actually sleep
        return

    # Mock task to track creation and cancellation
    class MockTask:
        def __init__(self):
            nonlocal task_create_calls
            task_create_calls += 1

        def cancel(self):
            nonlocal task_cancel_calls
            task_cancel_calls += 1

        def done(self):
            # Return False so task appears to be running
            return False

        def __await__(self):
            # Mock awaiting the task (for task cleanup)
            async def _await():
                return None
            return _await().__await__()

    # Apply mocks
    consumer.check_heartbeat = mock_check_heartbeat

    # Mock asyncio functions in the service_bus_consumer module
    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.asyncio.create_task", side_effect=lambda coro: MockTask()):

        try:
            # Run the supervisor - it will break out when KeyboardInterrupt is raised
            await consumer.supervisor_with_heartbeat_check()
        except KeyboardInterrupt:
            # Expected way to exit the infinite loop
            pass

    # Verify expected behavior occurred
    assert heartbeat_calls >= 2, f"Expected at least 2 heartbeat checks, got {heartbeat_calls}"
    assert task_create_calls >= 2, f"Expected at least 2 tasks created (initial + restart), got {task_create_calls}"
    assert task_cancel_calls >= 1, f"Expected at least 1 task cancellation, got {task_cancel_calls}"
    assert len(sleep_calls) >= 2, f"Expected at least 2 sleep calls, got {len(sleep_calls)}"
    assert 60 in sleep_calls, f"Expected sleep(60) for heartbeat check interval, got {sleep_calls}"
