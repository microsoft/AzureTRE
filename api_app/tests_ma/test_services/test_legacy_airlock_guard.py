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
    request_repo.get_data_retaining_airlock_request_ids_for_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_noop_when_no_version_in_patch():
    request_repo = AsyncMock()
    await ensure_airlock_version_change_allowed(_workspace(1), ResourcePatch(properties={"display_name": "x"}), request_repo)
    request_repo.get_data_retaining_airlock_request_ids_for_workspace.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_permits_change_when_no_in_flight():
    request_repo = AsyncMock()
    request_repo.get_data_retaining_airlock_request_ids_for_workspace.return_value = []
    await ensure_airlock_version_change_allowed(_workspace(1), ResourcePatch(properties={"airlock_version": 2}), request_repo)


@pytest.mark.asyncio
async def test_ensure_airlock_version_change_allowed_blocks_upgrade_with_in_flight_requests():
    request_repo = AsyncMock()
    request_repo.get_data_retaining_airlock_request_ids_for_workspace.return_value = ["req-1"]
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
    # enable_airlock defaults to true in the bundle, so an omitted value must still be treated as enabled.
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=False):
        with pytest.raises(ValueError):
            ensure_workspace_airlock_version_supported({"airlock_version": 1})


def test_ensure_workspace_airlock_version_supported_blocks_v2_on_manual_auth():
    # v2 needs the per-workspace app-registration signer, only created in automatic auth mode.
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        with pytest.raises(ValueError):
            ensure_workspace_airlock_version_supported({"enable_airlock": True, "airlock_version": 2, "auth_type": "Manual"})


def test_ensure_workspace_airlock_version_supported_allows_v2_on_automatic_auth():
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        ensure_workspace_airlock_version_supported({"enable_airlock": True, "airlock_version": 2, "auth_type": "Automatic"})


def test_ensure_workspace_airlock_version_supported_allows_manual_auth_when_version_unspecified():
    # Manual + unspecified version is fine here; it defaults to v1 at creation time.
    with patch("services.legacy_airlock_guard.config.ENABLE_LEGACY_AIRLOCK", new=True):
        ensure_workspace_airlock_version_supported({"enable_airlock": True, "auth_type": "Manual"})
