from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from auth.rbac import (
    require_workspace_owner_or_researcher,
    require_workspace_owner_or_researcher_or_airlock_manager,
)
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.airlock_request import AirlockActions, AirlockRequest, AirlockRequestStatus, AirlockRequestType
from models.domain.authentication import User
from models.domain.workspace import Workspace
from services.airlock import get_allowed_actions


WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"
REQUEST_ID = "00000000-0000-4000-8000-000000000002"
REQUEST_PATH = f"/api/workspaces/{WORKSPACE_ID}/requests/{REQUEST_ID}"
pytestmark = pytest.mark.asyncio


@pytest.fixture
def request_context(monkeypatch, app):
    creator = User(id="creator", name="Synthetic Creator", roles=["WorkspaceResearcher"])
    request = AirlockRequest(
        id=REQUEST_ID,
        workspaceId=WORKSPACE_ID,
        type="import",
        createdBy=creator,
        updatedBy=creator,
    )
    workspace = Workspace(
        id=WORKSPACE_ID,
        templateName="synthetic-workspace",
        templateVersion="1.0.0",
        etag="test",
    )
    state = SimpleNamespace(user=creator, request=request)
    overrides = app.dependency_overrides.copy()
    for dependency in (require_workspace_owner_or_researcher, require_workspace_owner_or_researcher_or_airlock_manager):
        app.dependency_overrides[dependency] = lambda: state.user
    monkeypatch.setattr(
        "db.repositories.workspaces.WorkspaceRepository.get_workspace_by_id", AsyncMock(return_value=workspace)
    )
    monkeypatch.setattr(
        "db.repositories.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", AsyncMock(return_value=workspace)
    )
    monkeypatch.setattr(
        AirlockRequestRepository, "read_item_by_id", AsyncMock(side_effect=lambda _: request.model_dump())
    )
    state.update = AsyncMock(return_value=request)
    monkeypatch.setattr("api.routes.airlock.update_and_publish_event_airlock_request", state.update)
    monkeypatch.setattr("services.airlock.update_and_publish_event_airlock_request", state.update)
    state.delete_review_resources = AsyncMock()
    monkeypatch.setattr("services.airlock.delete_all_review_user_resources", state.delete_review_resources)
    state.sign_sas = Mock(return_value="https://synthetic.invalid/container?sp=rwld")
    monkeypatch.setattr("services.airlock.get_airlock_request_container_sas_token", state.sign_sas)
    yield state
    app.dependency_overrides.clear()
    app.dependency_overrides.update(overrides)


@pytest.mark.parametrize("action", ["submit", "cancel", "link"])
@pytest.mark.parametrize("request_type", ["import", "export"])
@pytest.mark.parametrize("airlock_version", [1, 2])
@pytest.mark.parametrize(
    "actor,role,expected",
    [
        ("creator", "WorkspaceResearcher", 200),
        ("other-researcher", "WorkspaceResearcher", 403),
        ("workspace-owner", "WorkspaceOwner", 200),
    ],
)
async def test_draft_actions_require_creator_or_owner(
    client,
    request_context,
    action,
    request_type,
    airlock_version,
    actor,
    role,
    expected,
):
    state = request_context
    state.user = User(id=actor, name="Synthetic Caller", roles=[role])
    state.request.type = AirlockRequestType(request_type)
    state.request.airlock_version = airlock_version
    send = client.get if action == "link" else client.post
    response = await send(f"{REQUEST_PATH}/{action}")
    assert response.status_code == expected, response.text
    if expected == 403:
        state.update.assert_not_awaited()
        state.delete_review_resources.assert_not_awaited()
        state.sign_sas.assert_not_called()
    elif action == "link":
        state.sign_sas.assert_called_once()
    else:
        state.update.assert_awaited_once()


@pytest.mark.parametrize("actor,expected", [("creator", 200), ("other-researcher", 403)])
async def test_cancellation_in_review_requires_creator_or_owner(client, request_context, actor, expected):
    request_context.user = User(id=actor, name="Synthetic Caller", roles=["WorkspaceResearcher"])
    request_context.request.status = AirlockRequestStatus.InReview
    response = await client.post(f"{REQUEST_PATH}/cancel")
    assert response.status_code == expected, response.text
    if expected == 403:
        request_context.update.assert_not_awaited()
        request_context.delete_review_resources.assert_not_awaited()


@pytest.mark.parametrize("action", ["submit", "cancel", "link"])
async def test_missing_creator_does_not_grant_researcher_access(client, request_context, action):
    request_context.request.createdBy = {}
    send = client.get if action == "link" else client.post
    response = await send(f"{REQUEST_PATH}/{action}")
    assert response.status_code == 403, response.text
    request_context.update.assert_not_awaited()
    request_context.sign_sas.assert_not_called()


@pytest.mark.parametrize(
    "request_status,role,expected",
    [
        (AirlockRequestStatus.InReview, "AirlockManager", 200),
        (AirlockRequestStatus.InReview, "WorkspaceOwner", 200),
        (AirlockRequestStatus.InReview, "WorkspaceResearcher", 403),
        (AirlockRequestStatus.Approved, "WorkspaceResearcher", 200),
    ],
)
async def test_non_draft_link_permissions_are_preserved(client, request_context, request_status, role, expected):
    request_context.user = User(id="another-user", name="Synthetic Caller", roles=[role])
    request_context.request.status = request_status
    response = await client.get(f"{REQUEST_PATH}/link")
    assert response.status_code == expected, response.text


@pytest.mark.parametrize(
    "actor,role,expected",
    [
        ("creator", "WorkspaceResearcher", [AirlockActions.Cancel, AirlockActions.Submit]),
        ("other-researcher", "WorkspaceResearcher", []),
        ("workspace-owner", "WorkspaceOwner", [AirlockActions.Cancel, AirlockActions.Submit]),
        ("creator", "AirlockManager", []),
    ],
)
async def test_allowed_draft_actions_match_ownership_policy(request_context, actor, role, expected):
    user = User(id=actor, name="Synthetic Caller", roles=[role])
    actions = get_allowed_actions(request_context.request, user, AirlockRequestRepository())
    assert actions == expected
