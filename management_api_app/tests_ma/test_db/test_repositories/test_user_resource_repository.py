from mock import patch
import pytest

from db.errors import EntityDoesNotExist
from db.repositories.user_resources import UserResourceRepository
from models.domain.resource import Status, ResourceType
from models.domain.user_resource import UserResource
from models.schemas.user_resource import UserResourceInCreate


@pytest.fixture
def basic_user_resource_request():
    return UserResourceInCreate(userResourceType="user-resource-type", properties={"display_name": "test", "description": "test", "tre_id": "test"})


@pytest.fixture
def user_resource_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield UserResourceRepository(cosmos_client_mock)


@pytest.fixture
def user_resource():
    user_resource = UserResource(
        id="000000d3-82da-4bfc-b6e9-9a7853ef753e",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        resourceTemplateName="my-workspace-service",
    )
    return user_resource


@patch('db.repositories.user_resources.UserResourceRepository.validate_input_against_template')
@patch('core.config.TRE_ID', "9876")
def test_create_user_resource_item_creates_a_user_resource_with_the_right_values(validate_input_mock, user_resource_repo, basic_user_resource_request):
    user_resource_to_create = basic_user_resource_request
    validate_input_mock.return_value = basic_user_resource_request.userResourceType

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
    user_id = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
    user_resource = user_resource_repo.create_user_resource_item(user_resource_to_create, workspace_id, parent_workspace_service_id, "parent-service-type", user_id)

    assert user_resource.resourceTemplateName == basic_user_resource_request.userResourceType
    assert user_resource.resourceType == ResourceType.UserResource
    assert user_resource.deployment.status == Status.NotDeployed
    assert user_resource.workspaceId == workspace_id
    assert user_resource.parentWorkspaceServiceId == parent_workspace_service_id
    assert user_resource.ownerId == user_id
    assert len(user_resource.resourceTemplateParameters["tre_id"]) > 0
    # need to make sure request doesn't override system param
    assert user_resource.resourceTemplateParameters["tre_id"] != "test"


@patch('db.repositories.user_resources.UserResourceRepository.validate_input_against_template')
def test_create_user_resource_item_raises_value_error_if_template_is_invalid(validate_input_mock, user_resource_repo, basic_user_resource_request):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
    user_id = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
    validate_input_mock.side_effect = ValueError

    with pytest.raises(ValueError):
        user_resource_repo.create_user_resource_item(basic_user_resource_request, workspace_id, parent_workspace_service_id, "parent-service-type", user_id)


@patch('db.repositories.user_resources.UserResourceRepository.query', return_value=[])
def test_get_user_resources_for_workspace_queries_db(query_mock, user_resource_repo):
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"

    user_resource_repo.get_user_resources_for_workspace_service(parent_workspace_service_id)

    query_mock.assert_called_once_with(query='SELECT * FROM c WHERE c.resourceType = "user-resource" AND c.deployment.status != "deleted" AND c.parentWorkspaceServiceId = "937453d3-82da-4bfc-b6e9-9a7853ef753e"')


@patch('db.repositories.user_resources.UserResourceRepository.get_resource_dict_by_type_and_id')
def test_get_user_resource_returns_resource_if_found(get_resource_mock, user_resource_repo, user_resource):
    get_resource_mock.return_value = user_resource.dict()

    actual_resource = user_resource_repo.get_user_resource_by_id("000000d3-82da-4bfc-b6e9-9a7853ef753e")

    assert actual_resource == user_resource


@patch('db.repositories.user_resources.UserResourceRepository.query')
def test_get_user_resource_by_id_queries_db(query_mock, user_resource_repo, user_resource):
    query_mock.return_value = [user_resource.dict()]
    user_resource_repo.get_user_resource_by_id("000000d3-82da-4bfc-b6e9-9a7853ef753e")

    query_mock.assert_called_once_with(query='SELECT * FROM c WHERE c.deployment.status != "deleted" AND c.resourceType = "user-resource" AND c.id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"')


@patch('db.repositories.user_resources.UserResourceRepository.query', return_value=[])
def test_get_user_resource_by_id_raises_entity_does_not_exist_if_not_found(_, user_resource_repo):
    with pytest.raises(EntityDoesNotExist):
        user_resource_repo.get_user_resource_by_id("000000d3-82da-4bfc-b6e9-9a7853ef753e")
