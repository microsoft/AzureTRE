import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from service_bus.service_bus_consumer import ServiceBusConsumer


# Create a concrete implementation for testing
class TestConsumer(ServiceBusConsumer):
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
    consumer = TestConsumer()
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
        consumer = TestConsumer()
        result = consumer.check_heartbeat(max_age_seconds=300)
        assert result is True


@pytest.mark.asyncio
@patch("service_bus.service_bus_consumer.os.path.exists", return_value=True)
@patch("builtins.open", create=True)
async def test_check_heartbeat_stale(mock_open, mock_exists):
    """Test checking a stale heartbeat."""
    mock_open.return_value.__enter__.return_value.read.return_value = "1234567890.0"

    with patch("service_bus.service_bus_consumer.time.time", return_value=1234567890.0 + 400):  # 400 seconds later
        consumer = TestConsumer()
        result = consumer.check_heartbeat(max_age_seconds=300)
        assert result is False


@pytest.mark.asyncio
@patch("service_bus.service_bus_consumer.time.time", return_value=1234567890.0)
@patch("builtins.open", create=True)
async def test_update_heartbeat(mock_open, mock_time):
    """Test updating heartbeat."""
    consumer = TestConsumer()
    with patch("service_bus.service_bus_consumer.os.getpid", return_value=12345):
        consumer.worker_id = 12345  # Set worker_id explicitly for test
        consumer.update_heartbeat()

    import tempfile
    expected_path = f"{tempfile.gettempdir()}/test_consumer_heartbeat_12345.txt"
    mock_open.assert_called_once_with(expected_path, 'w')
    mock_open.return_value.__enter__.return_value.write.assert_called_once_with("1234567890.0")


@pytest.mark.asyncio
async def test_receive_messages_with_restart_check():
    """Test receive_messages_with_restart_check calls receive_messages."""
    consumer = TestConsumer()

    # Mock the receive_messages method to raise an exception after first call
    original_receive_messages = consumer.receive_messages
    call_count = 0

    async def mock_receive_messages():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await original_receive_messages()
        else:
            raise Exception("Test exception")

    consumer.receive_messages = mock_receive_messages

    # Mock asyncio.sleep to avoid actual waiting
    with patch("asyncio.sleep", new_callable=AsyncMock):
        # Schedule the coroutine and run it for a short time
        task = asyncio.create_task(consumer.receive_messages_with_restart_check())
        await asyncio.sleep(0.2)  # Give it a chance to run
        task.cancel()  # Cancel to exit the infinite loop

        try:
            await task
        except asyncio.CancelledError:
            pass

    assert consumer.receive_messages_called is True
    assert call_count > 0  # Should have called at least once


@pytest.mark.asyncio
async def test_supervisor_with_heartbeat_check():
    """Test supervisor_with_heartbeat_check manages the receive_messages task."""
    consumer = TestConsumer()

    # Mock check_heartbeat to control the test flow
    # Save original for potential future use
    # original_check_heartbeat = consumer.check_heartbeat
    heartbeat_calls = 0

    def mock_check_heartbeat(max_age_seconds=300):
        nonlocal heartbeat_calls
        heartbeat_calls += 1
        # First call returns True, second call returns False to trigger restart
        return heartbeat_calls != 2

    consumer.check_heartbeat = mock_check_heartbeat

    # Mock asyncio.sleep to avoid actual waiting
    with patch("asyncio.sleep", new_callable=AsyncMock):
        # Schedule the coroutine and run it for a short time
        task = asyncio.create_task(consumer.supervisor_with_heartbeat_check())
        await asyncio.sleep(0.2)  # Give it a chance to run
        task.cancel()  # Cancel to exit the infinite loop

        try:
            await task
        except asyncio.CancelledError:
            pass

    assert heartbeat_calls > 0  # Should have checked heartbeat at least once
