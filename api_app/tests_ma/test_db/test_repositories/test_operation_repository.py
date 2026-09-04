from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest_asyncio
import pytest
from mock import patch
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.operation import Operation, Status
from models.domain.request_action import RequestAction
from models.domain.resource import ResourceType
from db.repositories.resources import ResourceRepository
from db.repositories.operations import OperationRepository
from db.errors import EntityDoesNotExist
from resources import strings
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP

RESOURCE_ID = str(uuid.uuid4())
OPERATION_ID = str(uuid.uuid4())


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def operations_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        operations_repo = await OperationRepository.create()
        yield operations_repo


@pytest_asyncio.fixture
async def resource_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_repo = await ResourceRepository.create()
        yield resource_repo


@pytest_asyncio.fixture
async def resource_template_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_template_repo = await ResourceTemplateRepository.create()
        yield resource_template_repo


@patch('uuid.uuid4', side_effect=["random-uuid-1", "random-uuid-2", "random-uuid-3"])
@patch("db.repositories.operations.OperationRepository.get_timestamp", return_value=FAKE_CREATE_TIMESTAMP)
@patch("db.repositories.operations.OperationRepository.create_operation_id", return_value=OPERATION_ID)
async def test_create_operation_steps_from_multi_step_template(_, __, ___, resource_repo, test_user, multi_step_operation, operations_repo, basic_shared_service, resource_template_repo, multi_step_resource_template):

    expected_op = multi_step_operation
    expected_op.id = OPERATION_ID

    expected_op.status = Status.AwaitingDeployment
    expected_op.message = "This resource is waiting to be deployed"

    operations_repo.save_item = AsyncMock()
    resource_repo.get_active_resource_by_template_name = AsyncMock(return_value=basic_shared_service)
    resource_template_repo.get_template_by_name_and_version = AsyncMock(return_value=multi_step_resource_template)

    operation = await operations_repo.create_operation_item(
        resource_id="59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
        resource_list=[basic_shared_service.__dict__],
        action="install",
        resource_path="/workspaces/59b5c8e7-5c42-4fcb-a7fd-294cfc27aa76",
        resource_version=0,
        user=test_user,
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo

    )

    assert operation.model_dump() == expected_op.model_dump()


async def test_create_operation_steps_excludes_address_space_cleanup_for_cascade(
    resource_repo, test_user, operations_repo, basic_shared_service, resource_template_repo
):
    resource_template = MagicMock()
    resource_template.model_dump.return_value = {
        "name": "workspace-service",
        "resourceType": ResourceType.WorkspaceService,
        "pipeline": {
            "uninstall": [
                {"stepId": "main"},
                {
                    "stepId": strings.ADDRESS_SPACE_CLEANUP_STEP_ID,
                    "stepTitle": "Upgrade workspace",
                    "resourceType": ResourceType.Workspace,
                    "resourceAction": RequestAction.Upgrade,
                },
            ]
        }
    }
    resource_template_repo.get_template_by_name_and_version = AsyncMock(return_value=resource_template)
    operations_repo.save_item = AsyncMock()

    operation = await operations_repo.create_operation_item(
        resource_id="workspace-root",
        resource_list=[{**basic_shared_service.__dict__, "id": "descendant-service"}],
        action=RequestAction.UnInstall,
        resource_path="/workspaces/workspace-root",
        resource_version=0,
        user=test_user,
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo
    )

    assert [step.templateStepId for step in operation.steps] == ["main"]


async def test_resource_has_active_operation_returns_true_when_active_operation_exists(operations_repo):
    workspace_id = "7c5b2dc2-6b4c-4c7f-8d3e-1f5a9b0e2c4d"
    operations_repo.query = AsyncMock(return_value=[{"id": "op-1"}])
    result = await operations_repo.resource_has_active_operation(workspace_id)
    assert result is True
    operations_repo.query.assert_called_once()
    query_str = operations_repo.query.call_args[1]["query"] if "query" in operations_repo.query.call_args[1] else operations_repo.query.call_args[0][0]
    assert workspace_id in query_str
    assert "ARRAY_CONTAINS" in query_str
    assert f'CONTAINS(c.resourcePath, "{workspace_id}")' in query_str
    assert 'NOT CONTAINS(c.resourcePath, "/user-resources/")' not in query_str


async def test_resource_has_active_operation_returns_false_when_no_active_operation_exists(operations_repo):
    operations_repo.query = AsyncMock(return_value=[])
    result = await operations_repo.resource_has_active_operation("7c5b2dc2-6b4c-4c7f-8d3e-1f5a9b0e2c4d")
    assert result is False


async def test_resource_has_active_operation_returns_false_for_non_uuid_resource_id(operations_repo):
    operations_repo.query = AsyncMock()
    result = await operations_repo.resource_has_active_operation("not-a-uuid")
    assert result is False
    operations_repo.query.assert_not_called()


async def test_update_item_with_etag_calls_replace_item(operations_repo):
    from azure.core import MatchConditions
    operations_repo._container = MagicMock()
    operations_repo._container.replace_item = AsyncMock(return_value={"_etag": "\"new-etag\""})

    op = Operation(
        id="op-1",
        resourceId="res-1",
        resourcePath="/workspaces/res-1",
        action="install",
        etag="old-etag"
    )
    result = await operations_repo.update_item(op)

    operations_repo._container.replace_item.assert_awaited_once()
    call_kwargs = operations_repo._container.replace_item.call_args[1]
    assert call_kwargs["item"] == "op-1"
    assert call_kwargs["etag"] == "old-etag"
    assert call_kwargs["match_condition"] == MatchConditions.IfNotModified
    assert "etag" not in call_kwargs["body"]
    assert "_etag" not in call_kwargs["body"]
    assert result.etag == "new-etag"


async def test_update_item_without_etag_calls_upsert_item(operations_repo):
    operations_repo._container = MagicMock()
    operations_repo._container.upsert_item = AsyncMock(return_value={"_etag": "\"new-etag\""})

    op = Operation(
        id="op-1",
        resourceId="res-1",
        resourcePath="/workspaces/res-1",
        action="install",
    )
    result = await operations_repo.update_item(op)

    operations_repo._container.upsert_item.assert_awaited_once()
    call_kwargs = operations_repo._container.upsert_item.call_args[1]
    assert "etag" not in call_kwargs["body"]
    assert "_etag" not in call_kwargs["body"]
    assert result.etag == "new-etag"


async def test_save_item_excludes_etag_from_body(operations_repo):
    operations_repo._container = MagicMock()
    operations_repo._container.create_item = AsyncMock(return_value={"_etag": "\"created-etag\""})

    op = Operation(
        id="op-1",
        resourceId="res-1",
        resourcePath="/workspaces/res-1",
        action="install",
        etag="initial-etag"
    )
    await operations_repo.save_item(op)

    operations_repo._container.create_item.assert_awaited_once()
    call_kwargs = operations_repo._container.create_item.call_args[1]
    assert "etag" not in call_kwargs["body"]
    assert "_etag" not in call_kwargs["body"]
    assert op.etag == "created-etag"


async def test_update_item_raises_cosmos_access_condition_failed_error_on_mismatch(operations_repo):
    from azure.cosmos.exceptions import CosmosAccessConditionFailedError
    operations_repo._container = MagicMock()
    operations_repo._container.replace_item = AsyncMock(side_effect=CosmosAccessConditionFailedError())

    op = Operation(
        id="op-1",
        resourceId="res-1",
        resourcePath="/workspaces/res-1",
        action="install",
        etag="stale-etag"
    )
    with pytest.raises(CosmosAccessConditionFailedError):
        await operations_repo.update_item(op)


async def test_acquire_workspace_lease_creates_item(operations_repo):
    operations_repo._container = MagicMock()
    operations_repo._container.create_item = AsyncMock(return_value={})
    operations_repo.resource_has_active_operation = AsyncMock(return_value=False)

    res = await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert res is True
    operations_repo._container.create_item.assert_awaited_once()
    body = operations_repo._container.create_item.call_args[1]["body"]
    assert body["id"] == "lease_ws-1"
    assert body["workspaceId"] == "ws-1"
    assert body["operationId"] == "op-1"


async def test_acquire_workspace_lease_raises_409_if_active_operation_exists(operations_repo):
    from fastapi import HTTPException
    from azure.cosmos.exceptions import CosmosResourceExistsError
    operations_repo._container = MagicMock()
    operations_repo._container.create_item = AsyncMock(side_effect=CosmosResourceExistsError())
    now = operations_repo.get_timestamp()
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "other-op",
        "createdWhen": now,
    })
    active_op = MagicMock(status=Status.Deploying, updatedWhen=now, createdWhen=now)
    operations_repo.get_operation_by_id = AsyncMock(return_value=active_op)

    with pytest.raises(HTTPException) as exc:
        await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert exc.value.status_code == 409


async def test_acquire_workspace_lease_raises_409_if_existing_lease_operation_not_found(operations_repo):
    from fastapi import HTTPException
    from azure.cosmos.exceptions import CosmosResourceExistsError
    operations_repo._container = MagicMock()
    operations_repo.resource_has_active_operation = AsyncMock(return_value=False)
    operations_repo._container.create_item = AsyncMock(side_effect=CosmosResourceExistsError())
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "other-op",
        "createdWhen": operations_repo.get_timestamp(),
    })
    operations_repo.get_operation_by_id = AsyncMock(side_effect=EntityDoesNotExist())

    with pytest.raises(HTTPException) as exc:
        await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert exc.value.status_code == 409


async def test_acquire_workspace_lease_succeeds_if_same_operation_holds_lease(operations_repo):
    from azure.cosmos.exceptions import CosmosResourceExistsError
    operations_repo._container = MagicMock()
    operations_repo.resource_has_active_operation = AsyncMock(return_value=False)
    operations_repo._container.create_item = AsyncMock(side_effect=CosmosResourceExistsError())
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "op-1",
        "createdWhen": operations_repo.get_timestamp(),
    })

    res = await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert res is True


async def test_acquire_workspace_lease_replaces_lease_if_previous_operation_terminal(operations_repo):
    from azure.cosmos.exceptions import CosmosResourceExistsError
    operations_repo._container = MagicMock()
    operations_repo.resource_has_active_operation = AsyncMock(return_value=False)
    operations_repo._container.create_item = AsyncMock(side_effect=CosmosResourceExistsError())
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "other-op",
        "createdWhen": operations_repo.get_timestamp() - 1000,
        "_etag": "old-etag",
    })
    operations_repo.get_operation_by_id = AsyncMock(return_value=MagicMock(status=Status.Deployed))
    operations_repo._container.replace_item = AsyncMock(return_value={})

    res = await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert res is True
    operations_repo._container.replace_item.assert_awaited_once()


async def test_acquire_workspace_lease_reclaims_orphaned_lease_when_operation_not_found_after_expiry(operations_repo):
    from azure.cosmos.exceptions import CosmosResourceExistsError
    operations_repo._container = MagicMock()
    operations_repo.resource_has_active_operation = AsyncMock(return_value=False)
    operations_repo._container.create_item = AsyncMock(side_effect=CosmosResourceExistsError())
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "orphaned-op",
        "createdWhen": operations_repo.get_timestamp() - 4000,
        "_etag": "old-etag",
    })
    operations_repo.get_operation_by_id = AsyncMock(side_effect=EntityDoesNotExist())
    operations_repo._container.replace_item = AsyncMock(return_value={})

    res = await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert res is True
    operations_repo._container.replace_item.assert_awaited_once()


async def test_acquire_workspace_lease_retries_and_succeeds_when_lease_deleted_during_conflict_race(operations_repo):
    from azure.cosmos.exceptions import CosmosResourceExistsError, CosmosResourceNotFoundError
    operations_repo._container = MagicMock()
    operations_repo.resource_has_active_operation = AsyncMock(return_value=False)
    # 1st attempt: create fails with conflict, read fails because lease was deleted
    # 2nd attempt: create succeeds!
    operations_repo._container.create_item = AsyncMock(side_effect=[CosmosResourceExistsError(), {}])
    operations_repo.read_item_by_id = AsyncMock(side_effect=CosmosResourceNotFoundError())

    res = await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert res is True
    assert operations_repo._container.create_item.await_count == 2


async def test_release_workspace_lease_deletes_item(operations_repo):
    operations_repo._container = MagicMock()
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "op-1"
    })
    operations_repo.delete_item = AsyncMock()

    await operations_repo.release_workspace_lease("ws-1", "op-1")
    operations_repo.delete_item.assert_awaited_once_with("lease_ws-1")


async def test_release_workspace_lease_deletes_item_with_etag(operations_repo):
    from azure.core import MatchConditions
    operations_repo._container = MagicMock()
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "op-1",
        "_etag": "lease-etag",
    })
    operations_repo.delete_item = AsyncMock()

    await operations_repo.release_workspace_lease("ws-1", "op-1")
    operations_repo.delete_item.assert_awaited_once_with("lease_ws-1", etag="lease-etag", match_condition=MatchConditions.IfNotModified)


async def test_acquire_workspace_lease_reconciles_stale_active_operation_and_reacquires_lease(operations_repo):
    from azure.cosmos.exceptions import CosmosResourceExistsError
    operations_repo._container = MagicMock()
    # 1st attempt: conflict on create, reads lease, reconciles stale op, restarts loop
    # 2nd attempt: create succeeds because old lease was released by update_item
    operations_repo._container.create_item = AsyncMock(side_effect=[CosmosResourceExistsError(), {}])
    now = operations_repo.get_timestamp()
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "stale-op",
        "createdWhen": now - 4000,
        "_etag": "lease-etag",
    })
    stale_op = MagicMock(action="install", status=Status.AwaitingDeployment, updatedWhen=now - 4000, createdWhen=now - 4000)
    operations_repo.get_operation_by_id = AsyncMock(return_value=stale_op)
    operations_repo.update_item = AsyncMock()

    res = await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert res is True
    operations_repo.update_item.assert_awaited_once()
    assert stale_op.status == Status.DeploymentFailed
    assert operations_repo._container.create_item.await_count == 2


async def test_acquire_workspace_lease_fails_closed_when_reconciliation_fails(operations_repo):
    from fastapi import HTTPException
    from azure.cosmos.exceptions import CosmosResourceExistsError
    operations_repo._container = MagicMock()
    operations_repo._container.create_item = AsyncMock(side_effect=CosmosResourceExistsError())
    now = operations_repo.get_timestamp()
    operations_repo.read_item_by_id = AsyncMock(return_value={
        "id": "lease_ws-1",
        "operationId": "stale-op",
        "createdWhen": now - 4000,
        "_etag": "lease-etag",
    })
    stale_op = MagicMock(action="install", status=Status.AwaitingDeployment, updatedWhen=now - 4000, createdWhen=now - 4000)
    operations_repo.get_operation_by_id = AsyncMock(return_value=stale_op)
    operations_repo.update_item = AsyncMock(side_effect=Exception("Cosmos write error"))

    with pytest.raises(HTTPException) as exc:
        await operations_repo.acquire_workspace_lease("ws-1", "op-1")
    assert exc.value.status_code == 409


async def test_resource_has_active_operation_reconciles_stale_operation(operations_repo):
    now = operations_repo.get_timestamp()
    workspace_id = "7c5b2dc2-6b4c-4c7f-8d3e-1f5a9b0e2c4d"
    stale_op_dict = {
        "id": "op-stale",
        "resourceId": workspace_id,
        "resourcePath": f"/workspaces/{workspace_id}",
        "action": "install",
        "status": Status.AwaitingDeployment,
        "createdWhen": now - 4000,
        "updatedWhen": now - 4000,
    }
    operations_repo.query = AsyncMock(return_value=[stale_op_dict])
    operations_repo.update_item = AsyncMock()

    result = await operations_repo.resource_has_active_operation(workspace_id)
    assert result is False
    operations_repo.update_item.assert_awaited_once()
    saved_op = operations_repo.update_item.call_args[0][0]
    assert saved_op.status == Status.DeploymentFailed


async def test_resource_has_active_operation_fails_closed_when_reconciliation_fails(operations_repo):
    now = operations_repo.get_timestamp()
    workspace_id = "7c5b2dc2-6b4c-4c7f-8d3e-1f5a9b0e2c4d"
    stale_op_dict = {
        "id": "op-stale",
        "resourceId": workspace_id,
        "resourcePath": f"/workspaces/{workspace_id}",
        "action": "install",
        "status": Status.AwaitingDeployment,
        "createdWhen": now - 4000,
        "updatedWhen": now - 4000,
    }
    operations_repo.query = AsyncMock(return_value=[stale_op_dict])
    operations_repo.update_item = AsyncMock(side_effect=Exception("Cosmos write error"))

    result = await operations_repo.resource_has_active_operation(workspace_id)
    assert result is True


async def test_get_active_operations_for_resource_excludes_terminal_statuses(operations_repo):
    operations_repo.query = AsyncMock(return_value=[])

    await operations_repo.get_active_operations_for_resource("res-1")
    operations_repo.query.assert_awaited_once()
    query_str = operations_repo.query.call_args[1]["query"]
    assert 'c.resourceId = "res-1"' in query_str
    assert 'NOT ARRAY_CONTAINS(["deployed", "deployment_failed", "updated", "updating_failed", "deleted", "deleting_failed", "action_succeeded", "action_failed"], c.status)' in query_str


async def test_build_step_list_tolerates_missing_step_title(operations_repo):
    ws_id = str(uuid.uuid4())
    svc_id = str(uuid.uuid4())
    resource_template_dict = {
        "pipeline": {
            "upgrade": [
                {
                    "stepId": "step-1",
                    "resourceType": ResourceType.Workspace,
                    "resourceAction": RequestAction.Upgrade,
                }
            ]
        }
    }
    mock_resource_repo = MagicMock()
    mock_workspace = MagicMock(id=ws_id, templateName="tre-workspace", resourceType=ResourceType.Workspace)
    mock_service = MagicMock(id=svc_id, workspaceId=ws_id, resourceType=ResourceType.WorkspaceService)
    mock_resource_repo.get_resource_by_id = AsyncMock(side_effect=[mock_service, mock_workspace])

    steps = await operations_repo.build_step_list(
        steps=[],
        resource_template_dict=resource_template_dict,
        action="upgrade",
        resource_repo=mock_resource_repo,
        resource_id=svc_id,
        status=Status.AwaitingUpdate,
        message="updating",
    )
    assert len(steps) == 1
    assert steps[0].stepTitle is None
    assert steps[0].templateStepId == "step-1"
