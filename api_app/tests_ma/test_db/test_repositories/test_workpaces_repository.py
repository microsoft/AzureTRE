import copy
from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
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


@pytest_asyncio.fixture
async def workspace_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=MagicMock()):
        workspace_repo = await WorkspaceRepository().create()
        yield workspace_repo


@pytest_asyncio.fixture
async def operations_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=MagicMock()):
        operations_repo = await OperationRepository().create()
        yield operations_repo


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


@pytest.mark.asyncio
async def test_get_workspaces_queries_db(workspace_repo):
    workspace_repo.container.query_items = MagicMock()
    expected_query = workspace_repo.workspaces_query_string()

    await workspace_repo.get_workspaces()
    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=None)


@pytest.mark.asyncio
async def test_get_active_workspaces_queries_db(workspace_repo):
    workspace_repo.container.query_items = MagicMock()
    expected_query = workspace_repo.active_workspaces_query_string()

    await workspace_repo.get_active_workspaces()
    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=None)


@pytest.mark.asyncio
async def test_get_deployed_workspace_by_id_raises_resource_is_not_deployed_if_not_deployed(workspace_repo, workspace, operations_repo):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    sample_workspace = workspace

    workspace_repo.get_workspace_by_id = AsyncMock(return_value=sample_workspace)
    operations_repo.resource_has_deployed_operation = AsyncMock(return_value=False)

    with pytest.raises(ResourceIsNotDeployed):
        await workspace_repo.get_deployed_workspace_by_id(workspace_id, operations_repo)


@pytest.mark.asyncio
async def test_get_workspace_by_id_raises_entity_does_not_exist_if_item_does_not_exist(workspace_repo):
    workspace_id = uuid.uuid4()
    workspace_repo.container.query_items = MagicMock()

    with pytest.raises(EntityDoesNotExist):
        await workspace_repo.get_workspace_by_id(workspace_id)


@pytest.mark.asyncio
async def test_get_workspace_by_id_queries_db(workspace_repo, workspace):
    workspace_query_item_result = AsyncMock()
    workspace_query_item_result.__aiter__.return_value = [workspace.dict()]
    workspace_repo.container.query_items = MagicMock(return_value=workspace_query_item_result)
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.id = "{workspace.id}"'

    await workspace_repo.get_workspace_by_id(workspace.id)
    workspace_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=None)


@pytest.mark.asyncio
@patch('db.repositories.workspaces.generate_new_cidr')
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('db.repositories.workspaces.WorkspaceRepository.is_workspace_storage_account_available')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
async def test_create_workspace_item_creates_a_workspace_with_the_right_values(mock_is_workspace_storage_account_available, validate_input_mock, new_cidr_mock, workspace_repo, basic_workspace_request, basic_resource_template):
    workspace_to_create = basic_workspace_request
    # make sure the input has 'None' for values that we expect to be set
    workspace_to_create.properties.pop("address_space", None)
    workspace_to_create.properties.pop("address_spaces", None)
    workspace_to_create.properties.pop("workspace_owner_object_id", None)

    mock_is_workspace_storage_account_available.return_value = AsyncMock().return_value
    mock_is_workspace_storage_account_available.return_value.return_value = False
    validate_input_mock.return_value = basic_resource_template
    new_cidr_mock.return_value = "1.2.3.4/24"

    workspace, _ = await workspace_repo.create_workspace_item(workspace_to_create, {}, "test_object_id", ["test_role"])

    assert workspace.templateName == workspace_to_create.templateName
    assert workspace.resourceType == ResourceType.Workspace

    for key in ["display_name", "description", "azure_location", "workspace_id", "tre_id", "address_space", "workspace_owner_object_id"]:
        assert key in workspace.properties
        assert len(workspace.properties[key]) > 0

    # need to make sure request doesn't override system param
    assert workspace.properties["tre_id"] != workspace_to_create.properties["tre_id"]
    # a new CIDR was allocated
    assert workspace.properties["address_space"] == "1.2.3.4/24"
    # TODO: uncomment with https://github.com/microsoft/AzureTRE/pull/2902
    # assert workspace.properties["address_spaces"] == ["1.2.3.4/24"]
    assert workspace.properties["workspace_owner_object_id"] == "test_object_id"


@pytest.mark.asyncio
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
async def test_get_address_space_based_on_size_with_small_address_space(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "small"
    assert "10.1.4.0/24" == await workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)


@pytest.mark.asyncio
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
async def test_get_address_space_based_on_size_with_medium_address_space(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "medium"
    address_space = await workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)
    assert "10.1.4.0/22" == address_space


@pytest.mark.asyncio
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
async def test_get_address_space_based_on_size_with_large_address_space(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "large"
    address_space = workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)
    assert "10.0.0.0/16" == await address_space


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('db.repositories.workspaces.WorkspaceRepository.is_workspace_storage_account_available')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
async def test_create_workspace_item_creates_a_workspace_with_custom_address_space(mock_is_workspace_storage_account_available, validate_input_mock, workspace_repo, basic_workspace_request, basic_resource_template):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "custom"
    workspace_to_create.properties["address_space"] = "10.2.4.0/24"

    mock_is_workspace_storage_account_available.return_value = AsyncMock().return_value
    mock_is_workspace_storage_account_available.return_value.return_value = False
    validate_input_mock.return_value = basic_resource_template

    workspace, _ = await workspace_repo.create_workspace_item(workspace_to_create, {}, "test_object_id", ["test_role"])

    assert workspace.properties["address_space"] == workspace_to_create.properties["address_space"]


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('db.repositories.workspaces.WorkspaceRepository.is_workspace_storage_account_available')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
async def test_create_workspace_item_throws_exception_with_bad_custom_address_space(mock_is_workspace_storage_account_available, validate_input_mock, workspace_repo, basic_workspace_request, basic_resource_template):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "custom"
    workspace_to_create.properties["address_space"] = "192.168.0.0/24"

    mock_is_workspace_storage_account_available.return_value = AsyncMock().return_value
    mock_is_workspace_storage_account_available.return_value.return_value = False
    validate_input_mock.return_value = basic_resource_template

    with pytest.raises(InvalidInput):
        await workspace_repo.create_workspace_item(workspace_to_create, {}, "test_object_id", ["test_role"])


@pytest.mark.asyncio
async def test_get_address_space_based_on_size_with_custom_address_space_and_missing_address(workspace_repo, basic_workspace_request):
    workspace_to_create = basic_workspace_request
    workspace_to_create.properties["address_space_size"] = "custom"
    workspace_to_create.properties.pop("address_space", None)

    with pytest.raises(InvalidInput):
        await workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository.get_active_workspaces')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
async def test_get_address_space_based_on_size_with_address_space_only(get_active_workspaces_mock, workspace_repo, basic_workspace_request, workspace):
    workspace_with_address_space = copy.deepcopy(workspace)
    workspace_with_address_space.properties["address_space"] = "10.1.4.0/24"

    get_active_workspaces_mock.return_value = [workspace_with_address_space]
    workspace_to_create = basic_workspace_request
    address_space = await workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)

    assert "10.1.5.0/24" == address_space


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository.get_active_workspaces')
@patch('core.config.RESOURCE_LOCATION', "useast2")
@patch('core.config.TRE_ID', "9876")
@patch('core.config.CORE_ADDRESS_SPACE', "10.1.0.0/22")
@patch('core.config.TRE_ADDRESS_SPACE', "10.0.0.0/12")
async def test_get_address_space_based_on_size_with_address_space_and_address_spaces(get_active_workspaces_mock, workspace_repo, basic_workspace_request, workspace):
    workspace_with_address_space = copy.deepcopy(workspace)
    workspace_with_address_space.properties["address_space"] = "10.1.4.0/24"

    workspace_with_address_spaces = copy.deepcopy(workspace)
    workspace_with_address_spaces.properties["address_spaces"] = ["10.1.5.0/24", "10.1.6.0/24"]

    workspace_with_both = copy.deepcopy(workspace)
    workspace_with_both.properties["address_spaces"] = ["10.1.7.0/24", "10.1.8.0/24"]
    workspace_with_both.properties["address_space"] = "10.1.7.0/24"

    get_active_workspaces_mock.return_value = [workspace_with_address_space, workspace_with_address_spaces, workspace_with_both]
    workspace_to_create = basic_workspace_request
    address_space = await workspace_repo.get_address_space_based_on_size(workspace_to_create.properties)

    assert "10.1.9.0/24" == address_space


@pytest.mark.asyncio
@patch('db.repositories.workspaces.WorkspaceRepository.validate_input_against_template')
@patch('db.repositories.workspaces.WorkspaceRepository.is_workspace_storage_account_available')
async def test_create_workspace_item_raises_value_error_if_template_is_invalid(mock_is_workspace_storage_account_available, validate_input_mock, workspace_repo, basic_workspace_request):
    workspace_input = basic_workspace_request

    mock_is_workspace_storage_account_available.return_value = AsyncMock().return_value
    mock_is_workspace_storage_account_available.return_value.return_value = False
    validate_input_mock.side_effect = ValueError

    with pytest.raises(ValueError):
        await workspace_repo.create_workspace_item(workspace_input, {}, "test_object_id", ["test_role"])


def test_automatically_create_application_registration_returns_true(workspace_repo):
    dictToTest = {"auth_type": "Automatic"}

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


@pytest.mark.asyncio
@patch('db.repositories.workspaces.StorageManagementClient')
async def test_is_workspace_storage_account_available_when_name_available(mock_storage_client):
    workspace_id = "workspace1234"
    mock_storage_client.return_value = MagicMock()
    mock_storage_client.return_value.storage_accounts.check_name_availability.return_value = AsyncMock()
    mock_storage_client.return_value.storage_accounts.check_name_availability.return_value.name_available = True
    workspace_repo = WorkspaceRepository()

    result = await workspace_repo.is_workspace_storage_account_available(workspace_id)

    mock_storage_client.return_value.storage_accounts.check_name_availability.assert_called_once_with({"name": f"stgws{workspace_id[-4:]}"})
    assert result is True


@pytest.mark.asyncio
@patch('db.repositories.workspaces.StorageManagementClient')
async def test_is_workspace_storage_account_available_when_name_not_available(mock_storage_client):
    workspace_id = "workspace1234"
    mock_storage_client.return_value = MagicMock()
    mock_storage_client.return_value.storage_accounts.check_name_availability.return_value = AsyncMock()
    mock_storage_client.return_value.storage_accounts.check_name_availability.return_value.name_available = False
    workspace_repo = WorkspaceRepository()

    result = await workspace_repo.is_workspace_storage_account_available(workspace_id)

    mock_storage_client.return_value.storage_accounts.check_name_availability.assert_called_once_with({"name": f"stgws{workspace_id[-4:]}"})
    assert result is False
