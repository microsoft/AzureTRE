import uuid
from jsonschema.exceptions import ValidationError

from mock import patch, MagicMock
import pytest

import db.repositories.workspaces
from db.errors import EntityDoesNotExist
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, AuthenticationConfiguration, AuthProvider


@pytest.fixture
def basic_workspace_request():
    return WorkspaceInCreate(workspaceType="vanilla-tre", properties={"display_name": "test", "description": "test"})


@patch('azure.cosmos.CosmosClient')
def test_get_all_active_workspaces_calls_db_with_correct_query(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.query_items = MagicMock()
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false'

    workspace_repo.get_all_active_workspaces()

    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, enable_cross_partition_query=True)


@patch('azure.cosmos.CosmosClient')
def test_get_workspace_by_id_calls_db_with_correct_query(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_id = uuid.uuid4()
    return_workspace = {
        "id": str(workspace_id),
        "resourceTemplateName": "some-template-name",
        "resourceTemplateVersion": "1.0",
        "deployment": {"status": Status.NotDeployed, "message": ""}
    }
    workspace_repo.container.query_items = MagicMock(return_value=[return_workspace])
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.isDeleted = false AND c.id="{str(workspace_id)}"'

    workspace_repo.get_workspace_by_workspace_id(workspace_id)

    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, enable_cross_partition_query=True)


@patch('azure.cosmos.CosmosClient')
def test_get_workspace_by_id_throws_entity_does_not_exist_if_item_does_not_exist(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_id = uuid.uuid4()
    workspace_repo.container.query_items = MagicMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        workspace_repo.get_workspace_by_workspace_id(workspace_id)


@patch('db.repositories.workspaces.WorkspaceRepository._get_current_workspace_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_creates_a_workspace_with_the_right_values(cosmos_client_mock,
                                                                         _get_current_workspace_template_mock,
                                                                         basic_resource_template, basic_workspace_request):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    workspace_to_create = basic_workspace_request

    resource_template = basic_resource_template
    resource_template.required = ["display_name", "description"]

    _get_current_workspace_template_mock.return_value = basic_resource_template.dict()

    workspace = workspace_repo.create_workspace_item(workspace_to_create, {})

    assert workspace.displayName == basic_workspace_request.properties["display_name"]
    assert workspace.description == basic_workspace_request.properties["description"]
    assert workspace.resourceTemplateName == basic_workspace_request.workspaceType
    assert workspace.resourceType == ResourceType.Workspace
    assert workspace.deployment.status == Status.NotDeployed
    assert "azure_location" in workspace.resourceTemplateParameters
    assert "workspace_id" in workspace.resourceTemplateParameters
    assert "tre_id" in workspace.resourceTemplateParameters
    assert "address_space" in workspace.resourceTemplateParameters


@patch('db.repositories.workspaces.WorkspaceRepository._get_current_workspace_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_raises_value_error_if_template_is_invalid(cosmos_client_mock, _get_current_workspace_template_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    workspace_to_create = WorkspaceInCreate(
        workspaceType="vanilla-tre",
        displayName="my workspace",
        description="some description",
        authConfig=AuthenticationConfiguration(provider=AuthProvider.AAD, data={})
    )
    _get_current_workspace_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        workspace_repo.create_workspace_item(workspace_to_create, {})


@patch('azure.cosmos.CosmosClient')
def test_save_workspace_saves_the_items_to_the_database(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.create_item = MagicMock()
    workspace = Workspace(
        id="1234",
        resourceTemplateName="vanilla-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message="")
    )

    workspace_repo.save_workspace(workspace)

    workspace_repo.container.create_item.assert_called_once_with(body=workspace)


@patch('db.repositories.workspaces.WorkspaceRepository._get_current_workspace_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_does_not_accept_invalid_payload(cosmos_client_mock,
                                                               _get_current_workspace_template_mock,
                                                               basic_resource_template, basic_workspace_request):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    workspace_to_create = basic_workspace_request
    del workspace_to_create.properties["display_name"]

    resource_template = basic_resource_template
    resource_template.required = ["display_name"]

    _get_current_workspace_template_mock.return_value = resource_template.dict()

    with pytest.raises(ValidationError) as exc_info:
        workspace_repo.create_workspace_item(workspace_to_create, {})

    assert exc_info.value.message == "'display_name' is a required property"
