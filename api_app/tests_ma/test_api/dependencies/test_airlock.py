from mock import AsyncMock
import pytest
from fastapi import HTTPException

from api.dependencies.airlock import get_airlock_request_by_id_from_path
from models.domain.airlock_request import AirlockRequest, AirlockRequestType

pytestmark = pytest.mark.asyncio

WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
OTHER_WORKSPACE_ID = "d1f2a3b4-1111-2222-3333-444455556666"
AIRLOCK_REQUEST_ID = "af89dccd-cdf8-4e47-8cfe-995faeac0f09"


def _request(workspace_id):
    return AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        workspaceId=workspace_id,
        type=AirlockRequestType.Import,
        businessJustification="test")


async def test_returns_request_belonging_to_the_workspace_in_the_path():
    repo = AsyncMock()
    repo.get_airlock_request_by_id.return_value = _request(WORKSPACE_ID)

    result = await get_airlock_request_by_id_from_path(
        airlock_request_id=AIRLOCK_REQUEST_ID, workspace_id=WORKSPACE_ID, airlock_request_repo=repo)

    assert result.id == AIRLOCK_REQUEST_ID


async def test_rejects_request_belonging_to_another_workspace():
    # Authorisation is evaluated against the workspace in the path, so a request from a different
    # workspace must not be reachable by supplying its id.
    repo = AsyncMock()
    repo.get_airlock_request_by_id.return_value = _request(OTHER_WORKSPACE_ID)

    with pytest.raises(HTTPException) as exc:
        await get_airlock_request_by_id_from_path(
            airlock_request_id=AIRLOCK_REQUEST_ID, workspace_id=WORKSPACE_ID, airlock_request_repo=repo)

    assert exc.value.status_code == 404
