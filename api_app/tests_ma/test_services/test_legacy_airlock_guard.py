from unittest.mock import AsyncMock, patch
import pytest

from services.legacy_airlock_guard import (
    ensure_airlock_version_change_allowed,
    ensure_workspace_airlock_version_supported,
    run_legacy_airlock_migration_guard,
)
from models.schemas.resource import ResourcePatch


def _workspace(airlock_version=None):
    ws = AsyncMock()
    ws.id = "0b9c8928-9f25-4522-8f48-595105516531"
    ws.properties = {} if airlock_version is None else {"airlock_version": airlock_version}
    return ws


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_noop_when_version_unchanged():
    request_repo = AsyncMock()
    await ensure_airlock_version_change_allowed(_workspace(1), ResourcePatch(properties={"airlock_version": 1}), request_repo)
    request_repo.get_in_flight_airlock_request_ids_for_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_noop_when_no_version_in_patch():
    request_repo = AsyncMock()
    await ensure_airlock_version_change_allowed(_workspace(1), ResourcePatch(properties={"display_name": "x"}), request_repo)
    request_repo.get_in_flight_airlock_request_ids_for_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_permits_change_when_no_in_flight():
    request_repo = AsyncMock()
    request_repo.get_in_flight_airlock_request_ids_for_workspace.return_value = []
    await ensure_airlock_version_change_allowed(_workspace(1), ResourcePatch(properties={"airlock_version": 2}), request_repo)


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_blocks_upgrade_with_in_flight_requests():
    request_repo = AsyncMock()
    request_repo.get_in_flight_airlock_request_ids_for_workspace.return_value = ["req-1"]
    with pytest.raises(ValueError):
        await ensure_airlock_version_change_allowed(_workspace(1), ResourcePatch(properties={"airlock_version": 2}), request_repo)


def test_ensure_workspace_airlock_version_supported_allows_when_legacy_enabled():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        ensure_workspace_airlock_version_supported({"enable_airlock": True, "airlock_version": 1})


def test_ensure_workspace_airlock_version_supported_allows_v2_when_legacy_disabled():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False):
        ensure_workspace_airlock_version_supported({"enable_airlock": True, "airlock_version": 2})


def test_ensure_workspace_airlock_version_supported_blocks_v1_when_legacy_disabled():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False):
        with pytest.raises(ValueError):
            ensure_workspace_airlock_version_supported({"enable_airlock": True, "airlock_version": 1})


@pytest.mark.asyncio
@patch("services.legacy_airlock_guard.AirlockRequestRepository")
@patch("services.legacy_airlock_guard.WorkspaceRepository")
async def test_run_legacy_airlock_migration_guard_noop_when_legacy_enabled(mock_ws_repo, mock_req_repo):
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        await run_legacy_airlock_migration_guard()
    mock_ws_repo.create.assert_not_called()


@pytest.mark.asyncio
@patch("services.legacy_airlock_guard.AirlockRequestRepository")
@patch("services.legacy_airlock_guard.WorkspaceRepository")
async def test_run_legacy_airlock_migration_guard_blocks_on_v1_dependencies(mock_ws_repo, mock_req_repo):
    ws_repo = AsyncMock()
    ws_repo.get_active_v1_workspace_ids.return_value = ["ws-1"]
    mock_ws_repo.create = AsyncMock(return_value=ws_repo)
    req_repo = AsyncMock()
    req_repo.get_in_flight_v1_airlock_request_ids.return_value = []
    mock_req_repo.create = AsyncMock(return_value=req_repo)
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False), \
            patch("services.legacy_airlock_guard.config.BLOCK_DISABLE_LEGACY_AIRLOCK_IF_V1_EXISTS", new=True):
        with pytest.raises(RuntimeError):
            await run_legacy_airlock_migration_guard()
    # backfill runs in-process before the check (no dependency on the external db-migrate)
    ws_repo.set_default_airlock_version_for_legacy_workspaces.assert_awaited_once()
    req_repo.set_default_airlock_version_for_legacy_requests.assert_awaited_once()
