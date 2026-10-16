from unittest.mock import AsyncMock

import pytest

from auth.rbac import require_tre_user_or_admin, require_workspace_owner_or_researcher_or_airlock_manager
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.authentication import User
from models.domain.workspace import Workspace


WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"
ENDPOINTS = [
    ("/api/requests", {}),
    ("/api/requests", {"airlock_manager": True}),
    (f"/api/workspaces/{WORKSPACE_ID}/requests", {}),
]
INVALID_SORTS = [
    "updatedWhen DESC, c.id",
    "updatedWhen OFFSET 0 LIMIT 1",
    "updatedWhen; SELECT * FROM c",
    "unknownField",
    "",
]
VALID_SORTS = ["updatedWhen", "createdWhen", "createdTime", "title", "status", "type"]
pytestmark = pytest.mark.asyncio


@pytest.fixture
def request_queries(monkeypatch, app):
    user = User(id="synthetic-user", name="Synthetic Researcher", roles=["TREUser", "WorkspaceResearcher"])
    overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_workspace_owner_or_researcher_or_airlock_manager] = lambda: user
    app.dependency_overrides[require_tre_user_or_admin] = lambda: user
    workspace = Workspace(id=WORKSPACE_ID, templateName="test", templateVersion="1.0.0", etag="test")
    monkeypatch.setattr(
        "db.repositories.workspaces.WorkspaceRepository.get_workspace_by_id", AsyncMock(return_value=workspace)
    )
    monkeypatch.setattr(
        "db.repositories.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", AsyncMock(return_value=workspace)
    )
    queries = AsyncMock(return_value=[])
    monkeypatch.setattr(AirlockRequestRepository, "get_airlock_requests", queries)
    monkeypatch.setattr(AirlockRequestRepository, "get_airlock_requests_for_airlock_manager", queries)
    yield queries
    app.dependency_overrides.clear()
    app.dependency_overrides.update(overrides)


@pytest.mark.parametrize("endpoint,extra_params", ENDPOINTS)
@pytest.mark.parametrize("order_by", INVALID_SORTS)
async def test_api_rejects_unsupported_sort_before_querying(client, request_queries, endpoint, extra_params, order_by):
    response = await client.get(endpoint, params={"order_by": order_by, **extra_params})
    assert response.status_code == 422, response.text
    assert "order_by" in response.text
    request_queries.assert_not_awaited()


@pytest.mark.parametrize("endpoint,extra_params", ENDPOINTS)
@pytest.mark.parametrize("order_by", VALID_SORTS)
@pytest.mark.parametrize("ascending", [True, False])
async def test_api_accepts_existing_sort_options(client, request_queries, endpoint, extra_params, order_by, ascending):
    response = await client.get(endpoint, params={"order_by": order_by, "order_ascending": ascending, **extra_params})
    assert response.status_code == 200, response.text
    request_queries.assert_awaited_once()
    assert request_queries.call_args.kwargs["order_by"] == order_by
    assert request_queries.call_args.kwargs["order_ascending"] is ascending


@pytest.mark.parametrize(
    "error,expected",
    [(RuntimeError("synthetic database diagnostics"), 500), (ValueError("synthetic database diagnostics"), 400)],
)
async def test_request_errors_do_not_disclose_database_details(client, request_queries, error, expected):
    request_queries.side_effect = error
    response = await client.get("/api/requests")
    assert response.status_code == expected
    assert "synthetic database diagnostics" not in response.text


@pytest.mark.parametrize("order_by", INVALID_SORTS)
async def test_repository_rejects_unsupported_sort_before_querying(order_by):
    repo = AirlockRequestRepository()
    repo.query = AsyncMock(return_value=[])
    with pytest.raises(ValueError):
        await repo.get_airlock_requests(workspace_id=WORKSPACE_ID, creator_user_id="synthetic-user", order_by=order_by)
    repo.query.assert_not_awaited()


@pytest.mark.parametrize("order_by", VALID_SORTS)
@pytest.mark.parametrize("ascending", [True, False])
async def test_repository_sort_preserves_scope_and_normalises_legacy_field(order_by, ascending):
    repo = AirlockRequestRepository()
    repo.query = AsyncMock(return_value=[])
    await repo.get_airlock_requests(
        workspace_id=WORKSPACE_ID,
        creator_user_id="synthetic-user",
        order_by=order_by,
        order_ascending=ascending,
    )
    query = repo.query.call_args.kwargs["query"]
    field = "createdWhen" if order_by == "createdTime" else order_by
    assert query.endswith(f" ORDER BY c.{field} {'ASC' if ascending else 'DESC'}")
    assert "c.workspaceId=@workspace_id AND c.createdBy.id=@user_id" in query
    assert repo.query.call_args.kwargs["parameters"] == [
        {"name": "@workspace_id", "value": WORKSPACE_ID},
        {"name": "@user_id", "value": "synthetic-user"},
    ]
