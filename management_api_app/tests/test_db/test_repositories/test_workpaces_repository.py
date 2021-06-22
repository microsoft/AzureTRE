import uuid

from mock import patch, MagicMock
import pytest

import db.repositories.workspaces
from db.errors import EntityDoesNotExist, WorkspaceValidationError
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.resource_template import ResourceTemplate, Parameter
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, AuthenticationConfiguration, AuthProvider


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
@patch("db.repositories.workspaces.WorkspaceRepository._validate_workspace_parameters")
def test_create_workspace_item_creates_a_workspace_with_the_right_values(validate_workspace_parameters_mock, cosmos_client_mock, _get_current_workspace_template_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    workspace_type = "vanilla-tre"
    display_name = "my workspace"
    description = "some description"
    workspace_to_create = WorkspaceInCreate(
        workspaceType=workspace_type,
        displayName=display_name,
        description=description,
        authConfig=AuthenticationConfiguration(provider=AuthProvider.AAD, data={})
    )
    validate_workspace_parameters_mock.return_value = None
    _get_current_workspace_template_mock.return_value = ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name="sample",
        description="some description",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        parameters=[],
        current=False
    )

    workspace = workspace_repo.create_workspace_item(workspace_to_create, {})

    assert workspace.displayName == display_name
    assert workspace.description == description
    assert workspace.resourceTemplateName == workspace_type
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


@patch('azure.cosmos.CosmosClient')
def test_validate_workspace_parameters_no_parameters(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    template_parameters = []
    supplied_request_parameters = {}

    errors = workspace_repo._validate_workspace_parameters(template_parameters, supplied_request_parameters)

    assert errors is None


@patch('azure.cosmos.CosmosClient')
def test_validate_workspace_parameters_valid_parameters(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    template_parameters = [Parameter(name="a", type="string", default="a", applyto="a", description="b", required=True)]
    supplied_request_parameters = {"a": "b"}

    errors = workspace_repo._validate_workspace_parameters(template_parameters, supplied_request_parameters)

    assert errors is None


@patch('azure.cosmos.CosmosClient')
def test_validate_workspace_parameters_wrong_type(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    template_parameters = [Parameter(name="a", type="string", default="a", applyto="a", description="b", required=True)]
    supplied_request_parameters = {"a": 50}

    with pytest.raises(WorkspaceValidationError) as e:
        workspace_repo._validate_workspace_parameters(template_parameters, supplied_request_parameters)
    assert e.value.errors == {"Parameters with wrong type": [{"parameter": "a", "expected_type": "string", "supplied_type": "integer"}]}


@patch('azure.cosmos.CosmosClient')
def test_validate_workspace_parameters_extra_parameter(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    template_parameters = [Parameter(name="a", type="string", default="a", applyto="a", description="b", required=True)]
    supplied_request_parameters = {"a": "b", "b": "c"}

    with pytest.raises(WorkspaceValidationError) as e:
        workspace_repo._validate_workspace_parameters(template_parameters, supplied_request_parameters)
    assert e.value.errors == {"Invalid extra parameters": ["b"]}


@patch('azure.cosmos.CosmosClient')
def test_validate_workspace_parameters_missing_parameter(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    template_parameters = [Parameter(name="a", type="string", default="a", applyto="a", description="b", required=True)]
    supplied_request_parameters = {}

    with pytest.raises(WorkspaceValidationError) as e:
        workspace_repo._validate_workspace_parameters(template_parameters, supplied_request_parameters)
    assert e.value.errors == {"Missing required parameters": ["a"]}
