from unittest.mock import AsyncMock
import pytest

from services.legacy_airlock_guard import ensure_airlock_version_change_allowed
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
