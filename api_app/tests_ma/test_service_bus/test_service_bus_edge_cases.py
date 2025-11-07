import asyncio
import pytest
import os
from unittest.mock import patch, Mock
from service_bus.service_bus_consumer import ServiceBusConsumer


# Create a concrete implementation for testing edge cases
class MockConsumerForEdgeCases(ServiceBusConsumer):
    def __init__(self, skip_init=False):
        if not skip_init:
            super().__init__("test_consumer_edge")
        self.receive_messages_called = False

    async def receive_messages(self):
        self.receive_messages_called = True
        await asyncio.sleep(0.01)  # Small delay to make it a proper coroutine
        return


@pytest.mark.asyncio
async def test_heartbeat_file_corruption():
    """Test handling of corrupted heartbeat file."""
    consumer = MockConsumerForEdgeCases(skip_init=True)
    # Manually set required attributes to avoid init issues
    consumer.heartbeat_file = "/tmp/test_heartbeat_corruption.txt"

    with patch("service_bus.service_bus_consumer.os.path.exists", return_value=True), \
            patch("builtins.open") as mock_open:

        # Simulate corrupted file with invalid float content
        mock_open.return_value.__enter__.return_value.read.return_value = "not_a_number"

        result = consumer.check_heartbeat()
        assert result is False


@pytest.mark.asyncio
async def test_heartbeat_permission_denied():
    """Test heartbeat update when permission denied."""
    consumer = MockConsumerForEdgeCases(skip_init=True)
    consumer.heartbeat_file = "/tmp/test_heartbeat_permission.txt"

    with patch("builtins.open", side_effect=PermissionError("Permission denied")), \
            patch("service_bus.service_bus_consumer.logger") as mock_logger:

        # Should not crash, just log error
        consumer.update_heartbeat()
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_disk_full():
    """Test heartbeat update when disk is full."""
    consumer = MockConsumerForEdgeCases(skip_init=True)
    consumer.heartbeat_file = "/tmp/test_heartbeat_disk_full.txt"

    with patch("builtins.open", side_effect=OSError("No space left on device")), \
            patch("service_bus.service_bus_consumer.logger") as mock_logger:

        # Should not crash, just log error
        consumer.update_heartbeat()
        mock_logger.error.assert_called_once()


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

    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep), \
            patch("service_bus.service_bus_consumer.asyncio.create_task", side_effect=lambda coro: MockTask()), \
            patch.object(consumer, "check_heartbeat", return_value=True):

        try:
            await consumer.supervisor_with_heartbeat_check()
        except KeyboardInterrupt:
            pass

    # Verify task was created and cancelled during cleanup
    assert task_created, "Task should have been created"
    assert task_cancelled, "Task should have been cancelled during cleanup"


def test_restart_delay_configuration():
    """Test that restart delay configuration constants exist and have reasonable values."""
    # Import and test constants directly without creating consumer instances
    from service_bus.service_bus_consumer import (
        RESTART_DELAY_SECONDS,
        HEARTBEAT_CHECK_INTERVAL_SECONDS,
        HEARTBEAT_STALENESS_THRESHOLD_SECONDS,
        SUPERVISOR_ERROR_DELAY_SECONDS
    )

    # Validate configuration values
    assert RESTART_DELAY_SECONDS > 0, "Restart delay should be positive"
    assert RESTART_DELAY_SECONDS <= 10, "Restart delay should not be too long"
    assert HEARTBEAT_CHECK_INTERVAL_SECONDS > 0
    assert HEARTBEAT_STALENESS_THRESHOLD_SECONDS > HEARTBEAT_CHECK_INTERVAL_SECONDS
    assert SUPERVISOR_ERROR_DELAY_SECONDS > 0


def test_heartbeat_directory_creation():
    """Test that heartbeat directory is created if it doesn't exist."""
    consumer = MockConsumerForEdgeCases(skip_init=True)
    consumer.heartbeat_file = "/tmp/test_dir/test_heartbeat.txt"

    with patch("service_bus.service_bus_consumer.os.makedirs") as mock_makedirs, \
            patch("builtins.open", create=True) as mock_open:

        consumer.update_heartbeat()

        # Verify makedirs was called with exist_ok=True
        mock_makedirs.assert_called_once_with(
            os.path.dirname(consumer.heartbeat_file),
            exist_ok=True
        )
