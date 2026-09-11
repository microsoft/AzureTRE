from unittest.mock import AsyncMock
import uuid
import pytest_asyncio
import pytest
from mock import patch
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.operation import Status
from models.domain.resource import ResourceType
from models.domain.workspace_service import WorkspaceService
from models.domain.workspace import Workspace
from resources import strings
from db.repositories.resources import ResourceRepository
from db.repositories.operations import OperationRepository
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


async def test_create_uninstall_operation_adds_pending_address_space_cleanup(test_user, operations_repo, resource_repo, resource_template_repo, basic_workspace_service_template):
    workspace_id = str(uuid.uuid4())
    service = WorkspaceService(
        id=str(uuid.uuid4()),
        templateName="workspace-service",
        templateVersion="1.0.0",
        workspaceId=workspace_id,
        properties={"address_space": "10.0.0.0/24"},
        etag="etag",
        resourcePath="/workspaces/test/workspace-services/test"
    )
    workspace = Workspace(
        id=workspace_id,
        templateName="workspace",
        templateVersion="1.0.0",
        etag="etag",
        resourcePath="/workspaces/test",
        properties={"address_spaces": ["10.0.0.0/24"]}
    )
    resource_repo.get_resource_by_id = AsyncMock(return_value=workspace)
    resource_template_repo.get_template_by_name_and_version = AsyncMock(return_value=basic_workspace_service_template)
    operations_repo.save_item = AsyncMock()

    operation = await operations_repo.create_operation_item(
        resource_id=service.id,
        resource_list=[service.model_dump()],
        action="uninstall",
        resource_path=service.resourcePath,
        resource_version=service.resourceVersion,
        user=test_user,
        resource_repo=resource_repo,
        resource_template_repo=resource_template_repo
    )

    assert operation.addressSpaceCleanup.addressSpace == "10.0.0.0/24"
    assert operation.addressSpaceCleanup.workspaceId == workspace_id
    assert operation.addressSpaceCleanup.state.value == "pending"
    assert operation.steps[-1].templateStepId == strings.ADDRESS_SPACE_CLEANUP_STEP_ID
    assert operation.steps[-1].resourceType == ResourceType.Workspace
