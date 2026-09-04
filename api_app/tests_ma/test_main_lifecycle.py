import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_background_task_manager():
    from main import BackgroundTaskManager

    manager = BackgroundTaskManager()
    assert manager.is_shutting_down is False

    async def dummy():
        pass

    task = asyncio.create_task(dummy())
    manager.add(task)
    assert task in manager.get_tasks()

    manager.discard(task)
    assert task not in manager.get_tasks()

    await task


@pytest.mark.asyncio
@patch("main.bootstrap_database", return_value=True)
@patch("main.DeploymentStatusUpdater")
@patch("main.AirlockStatusUpdater")
async def test_lifespan_lifecycle_normal(mock_airlock, mock_deployment, mock_bootstrap):
    from main import BackgroundTaskManager, lifespan

    mock_deployment_instance = MagicMock()
    mock_deployment_instance.init_repos = AsyncMock()
    mock_deployment_instance.receive_messages = AsyncMock()
    mock_deployment.return_value = mock_deployment_instance

    mock_airlock_instance = MagicMock()
    mock_airlock_instance.init_repos = AsyncMock()
    mock_airlock_instance.receive_messages = AsyncMock()
    mock_airlock.return_value = mock_airlock_instance

    app = FastAPI()

    async with lifespan(app):
        assert hasattr(app.state, "background_tasks")
        assert isinstance(app.state.background_tasks, BackgroundTaskManager)
        tasks = app.state.background_tasks.get_tasks()
        assert len(tasks) == 2
        names = {t.get_name() for t in tasks}
        assert "deployment-status-updater" in names
        assert "airlock-status-updater" in names

    assert app.state.background_tasks.is_shutting_down is True


@pytest.mark.asyncio
@patch("main.bootstrap_database", return_value=True)
@patch("main.DeploymentStatusUpdater")
@patch("main.AirlockStatusUpdater")
@patch("main.logger")
async def test_lifespan_task_failure_during_runtime(mock_logger, mock_airlock, mock_deployment, mock_bootstrap):
    from main import lifespan

    mock_deployment_instance = MagicMock()
    mock_deployment_instance.init_repos = AsyncMock()

    async def fail_immediately():
        raise ValueError("Runtime failure")

    mock_deployment_instance.receive_messages = fail_immediately
    mock_deployment.return_value = mock_deployment_instance

    mock_airlock_instance = MagicMock()
    mock_airlock_instance.init_repos = AsyncMock()
    mock_airlock_instance.receive_messages = AsyncMock()
    mock_airlock.return_value = mock_airlock_instance

    app = FastAPI()

    async with lifespan(app):
        await asyncio.sleep(0.1)

    # Verify that the runtime failure was logged as an error
    error_logs = [call for call in mock_logger.error.call_args_list if "Background task deployment-status-updater failed" in call[0][0]]
    assert len(error_logs) == 1


@pytest.mark.asyncio
@patch("main.bootstrap_database", return_value=True)
@patch("main.DeploymentStatusUpdater")
@patch("main.AirlockStatusUpdater")
@patch("main.logger")
async def test_lifespan_task_failure_during_shutdown(mock_logger, mock_airlock, mock_deployment, mock_bootstrap):
    from main import lifespan

    mock_deployment_instance = MagicMock()
    mock_deployment_instance.init_repos = AsyncMock()

    async def raise_teardown_exception():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise RuntimeError("Database connection closed abruptly")

    mock_deployment_instance.receive_messages = raise_teardown_exception
    mock_deployment.return_value = mock_deployment_instance

    mock_airlock_instance = MagicMock()
    mock_airlock_instance.init_repos = AsyncMock()
    mock_airlock_instance.receive_messages = AsyncMock()
    mock_airlock.return_value = mock_airlock_instance

    app = FastAPI()

    async with lifespan(app):
        await asyncio.sleep(0.1)

    # The error should NOT be logged as error in _done_callback because it was gated on is_shutting_down
    for call in mock_logger.error.call_args_list:
        assert "Background task deployment-status-updater failed" not in call[0][0]

    # Instead, it should be caught during shutdown inspection and logged as warning
    warning_logs = [call for call in mock_logger.warning.call_args_list if "raised exception during shutdown" in call[0][0]]
    assert len(warning_logs) == 1
    assert "deployment-status-updater" in warning_logs[0][0][0]


@pytest.mark.asyncio
@patch("main.bootstrap_database", return_value=True)
@patch("main.DeploymentStatusUpdater")
@patch("main.AirlockStatusUpdater")
@patch("main.logger")
@patch("main.SHUTDOWN_TIMEOUT", 0.05)
async def test_lifespan_timeout_preserves_completed_task_exceptions(mock_logger, mock_airlock, mock_deployment, mock_bootstrap):
    from main import lifespan

    mock_deployment_instance = MagicMock()
    mock_deployment_instance.init_repos = AsyncMock()

    # Deployment updater completes quickly during cancellation by raising an exception
    async def raise_teardown_exception():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise RuntimeError("Deployment teardown failed")

    mock_deployment_instance.receive_messages = raise_teardown_exception
    mock_deployment.return_value = mock_deployment_instance

    hang_event = asyncio.Event()

    # Airlock updater suppresses cancellation and hangs past the timeout
    async def hang_on_cancellation():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            await hang_event.wait()

    mock_airlock_instance = MagicMock()
    mock_airlock_instance.init_repos = AsyncMock()
    mock_airlock_instance.receive_messages = hang_on_cancellation
    mock_airlock.return_value = mock_airlock_instance

    app = FastAPI()

    try:
        async with lifespan(app):
            await asyncio.sleep(0.01)

        # 1. Completed task exception is still inspected and logged as warning despite timeout
        warning_logs = [call for call in mock_logger.warning.call_args_list if "raised exception during shutdown" in call[0][0]]
        assert len(warning_logs) == 1
        assert "deployment-status-updater" in warning_logs[0][0][0]

        # 2. Timeout error is logged
        error_logs = [call for call in mock_logger.error.call_args_list if "Timeout waiting for background tasks to shutdown" in call[0][0]]
        assert len(error_logs) == 1

        # 3. Pending task is logged with warning
        pending_logs = [call for call in mock_logger.warning.call_args_list if "did not terminate in time during shutdown" in call[0][0]]
        assert len(pending_logs) == 1
        assert "airlock-status-updater" in pending_logs[0][0][0]
    finally:
        hang_event.set()
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
@patch("main.bootstrap_database", return_value=True)
@patch("main.DeploymentStatusUpdater")
@patch("main.AirlockStatusUpdater")
@patch("main.logger")
@patch("main.SHUTDOWN_TIMEOUT", 0.05)
async def test_lifespan_cancellation_suppression_strictly_bounded(mock_logger, mock_airlock, mock_deployment, mock_bootstrap):
    import time
    from main import lifespan

    mock_deployment_instance = MagicMock()
    mock_deployment_instance.init_repos = AsyncMock()

    hang_event = asyncio.Event()

    # Worker suppresses cancellation and ignores cancel signal
    async def suppress_cancellation():
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            await hang_event.wait()

    mock_deployment_instance.receive_messages = suppress_cancellation
    mock_deployment.return_value = mock_deployment_instance

    mock_airlock_instance = MagicMock()
    mock_airlock_instance.init_repos = AsyncMock()
    mock_airlock_instance.receive_messages = suppress_cancellation
    mock_airlock.return_value = mock_airlock_instance

    app = FastAPI()

    try:
        start_time = time.monotonic()
        async with lifespan(app):
            await asyncio.sleep(0.01)
        elapsed = time.monotonic() - start_time

        # Teardown should return promptly near SHUTDOWN_TIMEOUT and NOT hang
        assert elapsed < 0.5

        # Both tasks should be reported as pending
        pending_logs = [call for call in mock_logger.warning.call_args_list if "did not terminate in time during shutdown" in call[0][0]]
        assert len(pending_logs) == 2
    finally:
        hang_event.set()
        await asyncio.sleep(0.01)
