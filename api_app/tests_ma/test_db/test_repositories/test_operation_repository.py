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
    operations_repo.query = AsyncMock(return_value=[{"id": "op-1"}])
    result = await operations_repo.resource_has_active_operation("workspace-123")
    assert result is True
    operations_repo.query.assert_called_once()
    query_str = operations_repo.query.call_args[1]["query"] if "query" in operations_repo.query.call_args[1] else operations_repo.query.call_args[0][0]
    assert "workspace-123" in query_str
    assert "ARRAY_CONTAINS" in query_str
    assert 'CONTAINS(c.resourcePath, "workspace-123")' in query_str
    assert 'NOT CONTAINS(c.resourcePath, "/user-resources/")' in query_str


async def test_resource_has_active_operation_returns_false_when_no_active_operation_exists(operations_repo):
    operations_repo.query = AsyncMock(return_value=[])
    result = await operations_repo.resource_has_active_operation("workspace-123")
    assert result is False


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
