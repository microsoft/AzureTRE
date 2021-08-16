from jsonschema.exceptions import ValidationError

from mock import patch, MagicMock
import pytest
from db.errors import EntityDoesNotExist
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.workspace_service import WorkspaceService
from models.schemas.workspace_service import WorkspaceServiceInCreate


@pytest.fixture
def basic_workspace_service_request():
    return WorkspaceServiceInCreate(workspaceServiceType="workspace-service-type", properties={"display_name": "test", "description": "test"})


@patch('db.repositories.workspace_services.WorkspaceServiceRepository._get_current_workspace_service_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_creates_a_workspace_with_the_right_values(cosmos_client_mock, _get_current_workspace_service_template_mock, basic_workspace_service_template, basic_workspace_service_request):
    workspace_service_repo = WorkspaceServiceRepository(cosmos_client_mock)

    workspace_to_create = basic_workspace_service_request

    resource_template = basic_workspace_service_template
    resource_template.required = ["display_name", "description"]

    _get_current_workspace_service_template_mock.return_value = basic_workspace_service_template.dict()

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    workspace_service = workspace_service_repo.create_workspace_service_item(workspace_to_create, workspace_id)

    assert workspace_service.resourceTemplateName == basic_workspace_service_request.workspaceServiceType
    assert workspace_service.resourceType == ResourceType.WorkspaceService
    assert workspace_service.deployment.status == Status.NotDeployed
    assert workspace_service.workspaceId == workspace_id


@patch("jsonschema.validate", return_value=None)
@patch('db.repositories.workspace_services.WorkspaceServiceRepository._get_current_workspace_service_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_raises_value_error_if_template_is_invalid(cosmos_client_mock, _get_current_workspace_service_template_mock, __):
    workspace_service_repo = WorkspaceServiceRepository(cosmos_client_mock)

    workspace_service_to_create = WorkspaceServiceInCreate(workspaceServiceType="workspace-service-type")

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"

    _get_current_workspace_service_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        workspace_service_repo.create_workspace_service_item(workspace_service_to_create, workspace_id)


@patch('azure.cosmos.CosmosClient')
def test_save_workspace_saves_the_items_to_the_database(cosmos_client_mock):
    workspace_service_repo = WorkspaceServiceRepository(cosmos_client_mock)
    workspace_service_repo.container.create_item = MagicMock()
    workspace = WorkspaceService(
        id="1234",
        workspaceId="000000d3-82da-4bfc-b6e9-9a7853ef753e",
        resourceTemplateName="workspace-service-type",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message="")
    )

    workspace_service_repo.save_item(workspace)

    workspace_service_repo.container.create_item.assert_called_once_with(body=workspace)


@patch('db.repositories.workspace_services.WorkspaceServiceRepository._get_current_workspace_service_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_does_not_accept_invalid_payload(cosmos_client_mock, _get_current_workspace_service_template_mock, basic_workspace_service_template, basic_workspace_service_request):
    workspace_service_repo = WorkspaceServiceRepository(cosmos_client_mock)

    workspace_service_to_create = basic_workspace_service_request
    del workspace_service_to_create.properties["display_name"]

    resource_template = basic_workspace_service_template
    resource_template.required = ["display_name"]

    _get_current_workspace_service_template_mock.return_value = resource_template.dict()

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"

    with pytest.raises(ValidationError) as exc_info:
        workspace_service_repo.create_workspace_service_item(workspace_service_to_create, workspace_id)

    assert exc_info.value.message == "'display_name' is a required property"
