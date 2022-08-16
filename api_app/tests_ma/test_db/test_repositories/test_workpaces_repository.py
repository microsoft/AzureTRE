import pytest
from mock import patch, MagicMock
import uuid

from db.errors import EntityDoesNotExist, InvalidInput, ResourceIsNotDeployed
from db.repositories.operations import OperationRepository
from db.repositories.workspaces import WorkspaceRepository
from models.domain.resource import ResourceType
from models.domain.workspace import Workspace
from models.schemas.workspace import WorkspaceInCreate


@pytest.fixture
def basic_workspace_request():
    return WorkspaceInCreate(templateName="base-tre", properties={"display_name": "test", "description": "test", "client_id": "123", "tre_id": "test"})


@pytest.fixture
def workspace_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield WorkspaceRepository(cosmos_client_mock)


@pytest.fixture
def operations_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield OperationRepository(cosmos_client_mock)


@pytest.fixture
def workspace():
    workspace = Workspace(
        id="000000d3-82da-4bfc-b6e9-9a7853ef753e",
        templateVersion="0.1.0",
        etag="",
        properties={},
        templateName="my-workspace-service",
        resourcePath="test"
    )
    return workspace


def test_get_workspaces_queries_db(workspace_repo):
    workspace_repo.container.query_items = MagicMock()
    expected_query = workspace_repo.workspaces_query_string()

    workspace_repo.get_workspaces()
    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=None, enable_cross_partition_query=True)


def test_get_active_workspaces_queries_db(workspace_repo):
    workspace_repo.container.query_items = MagicMock()
    expected_query = workspace_repo.active_workspaces_query_string()

    workspace_repo.get_active_workspaces()
    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=None, enable_cross_partition_query=True)


def test_get_deployed_workspace_by_id_raises_resource_is_not_deployed_if_not_deployed(workspace_repo, workspace, operations_repo):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    sample_workspace = workspace

    workspace_repo.get_workspace_by_id = MagicMock(return_value=sample_workspace)
    operations_repo.resource_has_deployed_operation = MagicMock(return_value=False)

    with pytest.raises(ResourceIsNotDeployed):
        workspace_repo.get_deployed_workspace_by_id(workspace_id, operations_repo)


def test_get_workspace_by_id_raises_entity_does_not_exist_if_item_does_not_exist(workspace_repo):
    workspace_id = uuid.uuid4()
    workspace_repo.container.query_items = MagicMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        workspace_repo.get_workspace_by_id(workspace_id)


def test_get_workspace_by_id_queries_db(workspace_repo, workspace):
    workspace_repo.container.query_items = MagicMock(return_value=[workspace.dict()])
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.id = "{workspace.id}"'

    workspace_repo.get_workspace_by_id(workspace.id)
    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=None, enable_cross_partition_query=True)


@patch('db.repositories.workspaces.generate_new_cidr')
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
def test_create_workspace_item_creates_a_workspace_with_the_right_values(validate_input_mock, new_cidr_mock, workspace_repo, basic_workspace_request, basic_resource_template):
    workspace_to_create = basic_workspace_request
    # make sure the input has 'None' for values that we expect to be set
    workspace_to_create.properties.pop("address_space", None)
    workspace_to_create.properties.pop("workspace_owner_object_id", None)

    validate_input_mock.return_value = basic_resource_template
    new_cidr_mock.return_value = "1.2.3.4/24"

    workspace, _ = workspace_repo.create_workspace_item(workspace_to_create, {}, "test_object_id")

    assert workspace.templateName == workspace_to_create.templateName
    assert workspace.resourceType == ResourceType.Workspace

    for key in ["display_name", "description", "azure_location", "workspace_id", "tre_id", "address_space", "workspace_owner_object_id"]:
        assert key in workspace.properties
        assert len(workspace.properties[key]) > 0

    # need to make sure request doesn't override system param
    assert workspace.properties["tre_id"] != workspace_to_create.properties["tre_id"]
    # a new CIDR was allocated
    assert workspace.properties["address_space"] == "1.2.3.4/24"
    assert workspace.properties["workspace_owner_object_id"] == "test_object_id"


@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_get_address_space_based_on_size_with_small_address_space(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "small"
    assert "10.1.4.0/24" == workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)


@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_get_address_space_based_on_size_with_medium_address_space(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "medium"
    address_space = workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)
    assert "10.1.4.0/22" == address_space


@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_get_address_space_based_on_size_with_large_address_space(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "large"
    address_space = workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)
    assert "10.0.0.0/16" == address_space


@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_create_workspace_item_creates_a_workspace_with_custom_address_space(validate_input_mock, workspace_repo, basic_workspace_request, basic_resource_template):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "custom"
    workspace_to_create.properties["address_space"] = "10.2.4.0/24"
    validate_input_mock.return_value = basic_resource_template

    workspace, _ = workspace_repo.create_workspace_item(workspace_to_create, {}, "test_object_id")

    assert workspace.properties["address_space"] == workspace_to_create.properties["address_space"]


@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
def test_create_workspace_item_throws_exception_with_bad_custom_address_space(validate_input_mock, workspace_repo, basic_workspace_request, basic_resource_template):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "custom"
    workspace_to_create.properties["address_space"] = "192.168.0.0/24"
    validate_input_mock.return_value = basic_resource_template

    with pytest.raises(InvalidInput):
        workspace_repo.create_workspace_item(workspace_to_create, {}, "test_object_id")


def test_get_address_space_based_on_size_with_custom_address_space_and_missing_address(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "custom"
    workspace_to_create.properties.pop("address_space", None)

    with pytest.raises(InvalidInput):
        workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)


@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
def test_create_workspace_item_raises_value_error_if_template_is_invalid(validate_input_mock, workspace_repo, basic_workspace_request):
    workspace_input = basic_workspace_request
    validate_input_mock.side_effect = ValueError

    with pytest.raises(ValueError):
        workspace_repo.create_workspace_item(workspace_input, {}, "test_object_id")


def test_automatically_create_application_registration_returns_true(workspace_repo):
    dictToTest = {"client_id": "auto_create"}

    assert workspace_repo.automatically_create_application_registration(dictToTest) is True


def test_automatically_create_application_registration_returns_false(workspace_repo):
    dictToTest = {"client_id": "12345"}

    assert workspace_repo.automatically_create_application_registration(dictToTest) is False


def test_workspace_owner_is_set_if_not_present_in_workspace_properties(workspace_repo):
    dictToTest = {}
    expected_object_id = "Expected"

    assert workspace_repo.get_workspace_owner(dictToTest, expected_object_id) is expected_object_id


def test_workspace_owner_is_not_overwritten_if_present_in_workspace_properties(workspace_repo):
    dictToTest = {"workspace_owner_object_id": "Expected"}
    not_expected_object_id = "Not Expected"

    assert workspace_repo.get_workspace_owner(dictToTest, not_expected_object_id) == "Expected"
