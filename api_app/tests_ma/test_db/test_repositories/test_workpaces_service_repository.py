from unittest.mock import AsyncMock
from mock import patch, MagicMock
import pytest
import pytest_asyncio

from db.errors import EntityDoesNotExist, ResourceIsNotDeployed
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.operations import OperationRepository
from models.domain.resource import ResourceType
from models.domain.workspace_service import WorkspaceService
from models.schemas.workspace_service import WorkspaceServiceInCreate

pytestmark = pytest.mark.asyncio

WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
SERVICE_ID = "000000d3-82da-4bfc-b6e9-9a7853ef753e"


@pytest_asyncio.fixture
async def workspace_service_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=MagicMock()):
        workspace_repo = await WorkspaceServiceRepository().create()
        yield workspace_repo


@pytest_asyncio.fixture
async def operations_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=MagicMock()):
        operations_repo = await OperationRepository().create()
        yield operations_repo


@pytest.fixture
def basic_workspace_service_request():
    return WorkspaceServiceInCreate(templateName="workspace-service-type", properties={"display_name": "test", "description": "test", "tre_id": "test"})


@pytest.fixture
def workspace_service():
    workspace_service = WorkspaceService(
        id=SERVICE_ID,
        templateVersion="0.1.0",
        etag='',
        properties={},
        templateName="my-workspace-service",
        resourcePath="test"
    )
    return workspace_service


async def test_get_active_workspace_services_for_workspace_queries_db(workspace_service_repo):
    workspace_service_repo.query = AsyncMock(return_value=[])

    await workspace_service_repo.get_active_workspace_services_for_workspace(WORKSPACE_ID)

    workspace_service_repo.query.assert_called_once_with(query=WorkspaceServiceRepository.active_workspace_services_query(WORKSPACE_ID))


async def test_get_deployed_workspace_service_by_id_raises_resource_is_not_deployed_if_not_deployed(workspace_service_repo, workspace_service, operations_repo):
    service = workspace_service

    workspace_service_repo.get_workspace_service_by_id = AsyncMock(return_value=service)
    operations_repo.resource_has_deployed_operation = AsyncMock(return_value=False)

    with pytest.raises(ResourceIsNotDeployed):
        await workspace_service_repo.get_deployed_workspace_service_by_id(WORKSPACE_ID, SERVICE_ID, operations_repo)


async def test_get_deployed_workspace_service_by_id_return_workspace_service_if_deployed(workspace_service_repo, workspace_service, operations_repo):
    service = workspace_service

    workspace_service_repo.get_workspace_service_by_id = AsyncMock(return_value=service)
    operations_repo.resource_has_deployed_operation = AsyncMock(return_value=True)

    actual_service = await workspace_service_repo.get_deployed_workspace_service_by_id(WORKSPACE_ID, SERVICE_ID, operations_repo)

    assert actual_service == service


async def test_get_workspace_service_by_id_raises_entity_does_not_exist_if_no_available_services(workspace_service_repo):
    workspace_service_repo.query = AsyncMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        await workspace_service_repo.get_workspace_service_by_id(WORKSPACE_ID, SERVICE_ID)


async def test_get_workspace_service_by_id_queries_db(workspace_service_repo, workspace_service):
    workspace_service_repo.query = AsyncMock(return_value=[workspace_service])
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "workspace-service" AND c.workspaceId = "{WORKSPACE_ID}" AND c.id = "{SERVICE_ID}"'

    await workspace_service_repo.get_workspace_service_by_id(WORKSPACE_ID, SERVICE_ID)

    workspace_service_repo.query.assert_called_once_with(query=expected_query)


@patch('db.repositories.workspace_services.WorkspaceServiceRepository.validate_input_against_template')
@patch('core.config.TRE_ID', "9876")
async def test_create_workspace_service_item_creates_a_workspace_with_the_right_values(validate_input_mock, workspace_service_repo, basic_workspace_service_request, basic_workspace_service_template):
    workspace_service_to_create = basic_workspace_service_request

    resource_template = basic_workspace_service_template
    resource_template.required = ["display_name", "description"]

    validate_input_mock.return_value = basic_workspace_service_template

    workspace_service, _ = await workspace_service_repo.create_workspace_service_item(workspace_service_to_create, WORKSPACE_ID)

    assert workspace_service.templateName == basic_workspace_service_request.templateName
    assert workspace_service.resourceType == ResourceType.WorkspaceService
    assert workspace_service.workspaceId == WORKSPACE_ID
    assert len(workspace_service.properties["tre_id"]) > 0
    # need to make sure request doesn't override system param
    assert workspace_service.properties["tre_id"] != "test"


@patch('db.repositories.workspace_services.WorkspaceServiceRepository.validate_input_against_template', side_effect=ValueError)
async def test_create_workspace_item_raises_value_error_if_template_is_invalid(_, workspace_service_repo, basic_workspace_service_request):
    workspace_service_to_create = basic_workspace_service_request

    with pytest.raises(ValueError):
        await workspace_service_repo.create_workspace_service_item(workspace_service_to_create, WORKSPACE_ID)
