from mock import AsyncMock, patch
import pytest

from services.legacy_airlock_guard import run_legacy_airlock_migration_guard


@pytest.mark.asyncio
@patch("services.legacy_airlock_guard.WorkspaceRepository.create")
@patch("services.legacy_airlock_guard.AirlockRequestRepository.create")
async def test_guard_returns_when_legacy_airlock_enabled(request_repo_create_mock, workspace_repo_create_mock):
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        await run_legacy_airlock_migration_guard()

    workspace_repo_create_mock.assert_not_called()
    request_repo_create_mock.assert_not_called()


@pytest.mark.asyncio
@patch("services.legacy_airlock_guard.logger")
@patch("services.legacy_airlock_guard.WorkspaceRepository.create")
@patch("services.legacy_airlock_guard.AirlockRequestRepository.create")
async def test_guard_logs_info_when_no_v1_dependencies(request_repo_create_mock, workspace_repo_create_mock, logger_mock):
    workspace_repo = AsyncMock()
    workspace_repo.get_active_v1_workspace_ids.return_value = []
    workspace_repo_create_mock.return_value = workspace_repo

    request_repo = AsyncMock()
    request_repo.get_in_flight_v1_airlock_request_ids.return_value = []
    request_repo_create_mock.return_value = request_repo

    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False), \
            patch("services.legacy_airlock_guard.config.BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS", new=False):
        await run_legacy_airlock_migration_guard()

    logger_mock.info.assert_called_once()
    logger_mock.warning.assert_not_called()


@pytest.mark.asyncio
@patch("services.legacy_airlock_guard.logger")
@patch("services.legacy_airlock_guard.WorkspaceRepository.create")
@patch("services.legacy_airlock_guard.AirlockRequestRepository.create")
async def test_guard_logs_warning_when_v1_dependencies_exist_and_blocking_disabled(request_repo_create_mock, workspace_repo_create_mock, logger_mock):
    workspace_repo = AsyncMock()
    workspace_repo.get_active_v1_workspace_ids.return_value = ["workspace-1"]
    workspace_repo_create_mock.return_value = workspace_repo

    request_repo = AsyncMock()
    request_repo.get_in_flight_v1_airlock_request_ids.return_value = ["request-1"]
    request_repo_create_mock.return_value = request_repo

    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False), \
            patch("services.legacy_airlock_guard.config.BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS", new=False):
        await run_legacy_airlock_migration_guard()

    logger_mock.warning.assert_called_once()


@pytest.mark.asyncio
@patch("services.legacy_airlock_guard.WorkspaceRepository.create")
@patch("services.legacy_airlock_guard.AirlockRequestRepository.create")
async def test_guard_blocks_when_v1_dependencies_exist_and_blocking_enabled(request_repo_create_mock, workspace_repo_create_mock):
    workspace_repo = AsyncMock()
    workspace_repo.get_active_v1_workspace_ids.return_value = ["workspace-1"]
    workspace_repo_create_mock.return_value = workspace_repo

    request_repo = AsyncMock()
    request_repo.get_in_flight_v1_airlock_request_ids.return_value = []
    request_repo_create_mock.return_value = request_repo

    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False), \
            patch("services.legacy_airlock_guard.config.BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS", new=True):
        with pytest.raises(RuntimeError):
            await run_legacy_airlock_migration_guard()
