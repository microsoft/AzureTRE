from unittest.mock import AsyncMock, patch
import pytest

from services.legacy_airlock_guard import (
    ensure_airlock_version_change_allowed,
    ensure_workspace_airlock_version_supported,
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
async def test_ensure_airlock_version_change_allowed_blocks_disabling_v2_airlock():
    request_repo = AsyncMock()
    workspace = _workspace(2)
    workspace.properties["enable_airlock"] = True

    with pytest.raises(ValueError, match="Cannot disable Airlock"):
        await ensure_airlock_version_change_allowed(
            workspace, ResourcePatch(properties={"enable_airlock": False}), request_repo)

    request_repo.get_in_flight_airlock_request_ids_for_workspace.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_version", [None, "2", 2.0, True, 0, 3])
async def test_ensure_airlock_version_change_allowed_rejects_invalid_version(invalid_version):
    request_repo = AsyncMock()
    with pytest.raises(ValueError, match="integer with a value of 1 or 2"):
        await ensure_airlock_version_change_allowed(
            _workspace(1), ResourcePatch(properties={"airlock_version": invalid_version}), request_repo)
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


def test_ensure_workspace_airlock_version_supported_blocks_v1_when_enable_airlock_omitted():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False):
        with pytest.raises(ValueError):
            ensure_workspace_airlock_version_supported({"airlock_version": 1})


def test_unstamped_workspace_defaults_to_v1_legacy():
    # A missing airlock_version defaults to legacy (v1), so it is blocked when legacy is disabled.
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False):
        with pytest.raises(ValueError):
            ensure_workspace_airlock_version_supported({"enable_airlock": True})


def test_unstamped_workspace_is_treated_as_v1_when_validating_an_existing_one():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False):
        with pytest.raises(ValueError):
            ensure_workspace_airlock_version_supported({"enable_airlock": True}, default_version=1)


def test_ensure_workspace_airlock_version_supported_allows_v2_on_manual_auth():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        ensure_workspace_airlock_version_supported({"enable_airlock": True, "airlock_version": 2, "auth_type": "Manual"})


def test_ensure_workspace_airlock_version_supported_allows_v2_on_automatic_auth():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        ensure_workspace_airlock_version_supported({"enable_airlock": True, "airlock_version": 2, "auth_type": "Automatic"})


def test_unspecified_version_with_manual_auth_defaults_to_v1_and_is_blocked_when_legacy_disabled():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False):
        with pytest.raises(ValueError):
            ensure_workspace_airlock_version_supported({"enable_airlock": True, "auth_type": "Manual"})


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_blocks_downgrade():
    request_repo = AsyncMock()
    with pytest.raises(ValueError, match="downgrading is not supported"):
        await ensure_airlock_version_change_allowed(_workspace(2), ResourcePatch(properties={"airlock_version": 1}), request_repo)
    # A downgrade must be rejected outright, before even checking in-flight requests.
    request_repo.get_in_flight_airlock_request_ids_for_workspace.assert_not_called()
