import pytest
from mock import patch, MagicMock
import uuid

from db.errors import EntityDoesNotExist, ResourceIsNotDeployed
from db.repositories.workspaces import WorkspaceRepository
from models.domain.resource import Deployment, Status, ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate, WorkspacePatchEnabled


@pytest.fixture
def basic_workspace_request():
    return WorkspaceInCreate(templateName="base-tre", properties={"display_name": "test", "description": "test", "app_id": "123", "tre_id": "test"})


@pytest.fixture
def workspace_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield WorkspaceRepository(cosmos_client_mock)


@pytest.fixture
def workspace():
    workspace = Workspace(
        id="000000d3-82da-4bfc-b6e9-9a7853ef753e",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        resourceTemplateName="my-workspace-service",
    )
    return workspace


def test_get_active_workspaces_queries_db(workspace_repo):
    workspace_repo.container.query_items = MagicMock()
    expected_query = workspace_repo.active_workspaces_query_string()

    workspace_repo.get_active_workspaces()

    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, enable_cross_partition_query=True)


def test_get_deployed_workspace_by_id_raises_resource_is_not_deployed_if_not_deployed(workspace_repo, workspace):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    sample_workspace = workspace
    sample_workspace.deployment = Deployment(status=Status.NotDeployed)

    workspace_repo.get_workspace_by_id = MagicMock(return_value=sample_workspace)

    with pytest.raises(ResourceIsNotDeployed):
        workspace_repo.get_deployed_workspace_by_id(workspace_id)


def test_get_workspace_by_id_raises_entity_does_not_exist_if_item_does_not_exist(workspace_repo):
    workspace_id = uuid.uuid4()
    workspace_repo.container.query_items = MagicMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        workspace_repo.get_workspace_by_id(workspace_id)


def test_get_workspace_by_id_queries_db(workspace_repo, workspace):
    workspace_repo.container.query_items = MagicMock(return_value=[workspace.dict()])
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.deployment.status != "deleted" AND c.id = "{workspace.id}"'

    workspace_repo.get_workspace_by_id(workspace.id)

    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, enable_cross_partition_query=True)


@patch('db.repositories.workspaces.extract_auth_information', return_value={})
@patch('db.repositories.workspaces.generate_new_cidr')
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
def test_create_workspace_item_creates_a_workspace_with_the_right_values(validate_input_mock, new_cidr_mock, _, workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    # make sure the input doesn't include an address_space so that one will be generated
    workspace_to_create.properties.pop("address_space", None)

    validate_input_mock.return_value = workspace_to_create.templateName
    new_cidr_mock.return_value = "1.2.3.4/24"

    workspace = workspace_repo.create_workspace_item(workspace_to_create)

    assert workspace.resourceTemplateName == workspace_to_create.templateName
    assert workspace.resourceType == ResourceType.Workspace
    assert workspace.deployment.status == Status.NotDeployed

    for key in ["display_name", "description", "azure_location", "workspace_id", "tre_id", "address_space"]:
        assert key in workspace.resourceTemplateParameters
        assert len(workspace.resourceTemplateParameters[key]) > 0

    # need to make sure request doesn't override system param
    assert workspace.resourceTemplateParameters["tre_id"] != workspace_to_create.properties["tre_id"]
    # a new CIDR was allocated
    assert workspace.resourceTemplateParameters["address_space"] == "1.2.3.4/24"


@patch('db.repositories.workspaces.extract_auth_information', return_value={})
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
def test_create_workspace_item_creates_a_workspace_with_custom_address_space(validate_input_mock, _, workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space"] = "192.168.0.0/24"
    validate_input_mock.return_value = workspace_to_create.templateName

    workspace = workspace_repo.create_workspace_item(workspace_to_create)

    assert workspace.resourceTemplateParameters["address_space"] == workspace_to_create.properties["address_space"]


@patch('db.repositories.workspaces.extract_auth_information', return_value={})
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
def test_create_workspace_item_raises_value_error_if_template_is_invalid(validate_input_mock, _, workspace_repo, basic_workspace_request):
    workspace_input = basic_workspace_request
    validate_input_mock.side_effect = ValueError

    with pytest.raises(ValueError):
        workspace_repo.create_workspace_item(workspace_input)


def test_patch_workspace_updates_item(workspace_repo):
    workspace_repo.update_item = MagicMock(return_value=None)
    workspace_to_patch = Workspace(
        id="1234",
        resourceTemplateName="base-tre",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
    )
    workspace_patch = WorkspacePatchEnabled(enabled=False)

    workspace_repo.patch_workspace(workspace_to_patch, workspace_patch)

    workspace_to_patch.resourceTemplateParameters["enabled"] = False
    workspace_repo.update_item.assert_called_once_with(workspace_to_patch)
