import pytest
from mock import patch, MagicMock
from jsonschema.exceptions import ValidationError
import uuid

from db.errors import EntityDoesNotExist
import db.repositories.workspaces
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, WorkspacePatchEnabled


@pytest.fixture
def basic_workspace_request():
    return WorkspaceInCreate(workspaceType="vanilla-tre", properties={"display_name": "test", "description": "test", "app_id": "123"})


@pytest.fixture
def basic_workspace_template(basic_resource_template):
    basic_resource_template.resourceType = ResourceType.Workspace
    basic_resource_template.required = ["display_name", "description"]
    basic_resource_template.properties = {
        "display_name": {
            "type": "string",
            "title": "Name for the workspace",
            "description": "The name of the workspace to be displayed to users"
        },
        "description": {
            "type": "string",
            "title": "Description of the workspace",
            "description": "Description of the workspace"
        },
        "address_space": {
            "type": "string",
            "title": "Address space",
            "description": "Network address space to be used by the workspace"
        },
        "enabled": {
            "type": "boolean",
            "title": "Is the workspace enabled",
            "description": "Is the workspace enabled"
        }
    }
    return basic_resource_template


@patch('azure.cosmos.CosmosClient')
def test_get_all_active_workspaces_calls_db_with_correct_query(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.query_items = MagicMock()
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.deleted = false'

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
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.deleted = false AND c.id="{str(workspace_id)}"'

    workspace_repo.get_workspace_by_workspace_id(workspace_id)

    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, enable_cross_partition_query=True)


@patch('azure.cosmos.CosmosClient')
def test_get_workspace_by_id_throws_entity_does_not_exist_if_item_does_not_exist(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_id = uuid.uuid4()
    workspace_repo.container.query_items = MagicMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        workspace_repo.get_workspace_by_workspace_id(workspace_id)


@patch('db.repositories.workspaces.extract_auth_information', return_value={})
@patch('db.repositories.workspaces.WorkspaceRepository._validate_resource_parameters')
@patch('db.repositories.workspaces.WorkspaceRepository._get_current_workspace_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_creates_a_workspace_with_the_right_values(cosmos_client_mock, _get_current_workspace_template_mock, _validate_workspace_parameter_mock, _extract_auth_info_mock, basic_workspace_template, basic_workspace_request):

    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_to_create = basic_workspace_request
    _get_current_workspace_template_mock.return_value = basic_workspace_template

    workspace = workspace_repo.create_workspace_item(workspace_to_create)

    assert workspace.resourceTemplateName == basic_workspace_request.workspaceType
    assert workspace.resourceType == ResourceType.Workspace
    assert workspace.deployment.status == Status.NotDeployed
    assert "display_name" in workspace.resourceTemplateParameters
    assert "description" in workspace.resourceTemplateParameters
    assert "azure_location" in workspace.resourceTemplateParameters
    assert "workspace_id" in workspace.resourceTemplateParameters
    assert "tre_id" in workspace.resourceTemplateParameters
    assert "address_space" in workspace.resourceTemplateParameters


@patch("jsonschema.validate", return_value=None)
@patch('db.repositories.workspaces.extract_auth_information', return_value={})
@patch('db.repositories.workspaces.WorkspaceRepository._get_current_workspace_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_raises_value_error_if_template_is_invalid(cosmos_client_mock, _get_current_workspace_template_mock, _, __):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    workspace_to_create = WorkspaceInCreate(workspaceType="vanilla-tre")
    _get_current_workspace_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        workspace_repo.create_workspace_item(workspace_to_create)


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


@patch('db.repositories.workspaces.extract_auth_information', return_value={})
@patch('db.repositories.workspaces.WorkspaceRepository._get_current_workspace_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_does_not_accept_invalid_payload(cosmos_client_mock, _get_current_workspace_template_mock, _, basic_resource_template, basic_workspace_request):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)

    workspace_to_create = basic_workspace_request
    del workspace_to_create.properties["display_name"]

    resource_template = basic_resource_template
    resource_template.required = ["display_name"]

    _get_current_workspace_template_mock.return_value = resource_template

    with pytest.raises(ValidationError) as exc_info:
        workspace_repo.create_workspace_item(workspace_to_create)

    assert exc_info.value.message == "'display_name' is a required property"


@patch('azure.cosmos.CosmosClient')
def test_patch_workspace_updates_item(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.upsert_item = MagicMock()
    workspace_to_patch = Workspace(
        id="1234",
        resourceTemplateName="vanilla-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
    )
    workspace_patch = WorkspacePatchEnabled(enabled=False)
    patched_workspace_dict = workspace_to_patch.dict()
    patched_workspace_dict["resourceTemplateParameters"]["enabled"] = False

    workspace_repo.patch_workspace(workspace_to_patch, workspace_patch)

    workspace_repo.container.upsert_item.assert_called_once_with(body=patched_workspace_dict)
    assert workspace_to_patch.resourceTemplateParameters["enabled"] is False


@patch('azure.cosmos.CosmosClient')
def test_delete_workspace_marks_workspace_as_deleted(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.upsert_item = MagicMock()

    workspace = Workspace(
        id="1234",
        resourceTemplateName="vanilla-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
        deleted=False
    )
    workspace_repo.mark_workspace_as_deleted(workspace)
    workspace.deleted = True
    workspace_repo.container.upsert_item.assert_called_once_with(body=workspace)


@patch('azure.cosmos.CosmosClient')
def test_mark_workspace_as_not_deleted_marks_workspace_as_not_deleted(cosmos_client_mock):
    workspace_repo = db.repositories.workspaces.WorkspaceRepository(cosmos_client_mock)
    workspace_repo.container.upsert_item = MagicMock()

    workspace = Workspace(
        id="1234",
        resourceTemplateName="vanilla-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
        deleted=True
    )
    workspace_repo.mark_workspace_as_not_deleted(workspace)
    workspace.deleted = False
    workspace_repo.container.upsert_item.assert_called_once_with(body=workspace)
