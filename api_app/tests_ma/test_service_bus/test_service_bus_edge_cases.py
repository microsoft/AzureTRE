import asyncio
import pytest
import os
from unittest.mock import patch, Mock
from service_bus.service_bus_consumer import ServiceBusConsumer


# Create a concrete implementation for testing edge cases
class MockConsumerForEdgeCases(ServiceBusConsumer):
    def __init__(self):
        super().__init__("test_consumer_edge")
        self.receive_messages_called = False

    async def receive_messages(self):
        self.receive_messages_called = True
        await asyncio.sleep(0.1)
        return


@pytest.mark.asyncio
async def test_heartbeat_file_corruption():
    """Test handling of corrupted heartbeat file."""
    consumer = MockConsumerForEdgeCases()
    
    with patch("service_bus.service_bus_consumer.os.path.exists", return_value=True), \
         patch("builtins.open") as mock_open:
        
        # Simulate corrupted file with invalid float content
        mock_open.return_value.__enter__.return_value.read.return_value = "not_a_number"
        
        result = consumer.check_heartbeat()
        assert result is False


@pytest.mark.asyncio
async def test_heartbeat_permission_denied():
    """Test heartbeat update when permission denied."""
    consumer = MockConsumerForEdgeCases()
    
    with patch("builtins.open", side_effect=PermissionError("Permission denied")), \
         patch("service_bus.service_bus_consumer.logger") as mock_logger:
        
        # Should not crash, just log error
        consumer.update_heartbeat()
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_disk_full():
    """Test heartbeat update when disk is full."""
    consumer = MockConsumerForEdgeCases()
    
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


@pytest.mark.asyncio
async def test_rapid_task_failures():
    """Test supervisor behavior with rapid consecutive failures."""
    consumer = MockConsumerForEdgeCases()
    
    failure_count = 0
    sleep_calls = []
    max_failures = 2
    
    async def failing_receive_messages():
        nonlocal failure_count
        failure_count += 1
        if failure_count <= max_failures:
            raise Exception(f"Failure {failure_count}")
        # Success after max failures - but don't run forever
        return
    
    async def mock_sleep(duration):
        sleep_calls.append(duration)
        return  # Don't actually sleep
    
    # Override receive_messages to simulate failures
    consumer.receive_messages = failing_receive_messages
    
    with patch("service_bus.service_bus_consumer.asyncio.sleep", side_effect=mock_sleep):
        # Test restart behavior by calling directly
        for _ in range(max_failures + 1):  # Run enough times to trigger failures and success
            try:
                await consumer.receive_messages_with_restart_check()
                break  # Exit when successful
            except Exception:
                continue  # Continue to trigger restart logic
    
    # Verify restart delays were applied
    from service_bus.service_bus_consumer import RESTART_DELAY_SECONDS
    assert failure_count >= max_failures, f"Should have {max_failures} failures, got {failure_count}"
    assert len(sleep_calls) >= max_failures, f"Should have {max_failures} restart delays, got {len(sleep_calls)}"


@pytest.mark.asyncio
async def test_heartbeat_directory_creation():
    """Test that heartbeat directory is created if it doesn't exist."""
    consumer = MockConsumerForEdgeCases()
    
    with patch("service_bus.service_bus_consumer.os.makedirs") as mock_makedirs, \
         patch("builtins.open", create=True) as mock_open:
        
        consumer.update_heartbeat()
        
        # Verify makedirs was called with exist_ok=True
        mock_makedirs.assert_called_once_with(
            os.path.dirname(consumer.heartbeat_file), 
            exist_ok=True
        )