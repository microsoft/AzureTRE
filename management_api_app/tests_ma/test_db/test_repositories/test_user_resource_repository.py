from mock import patch
import pytest
from db.repositories.user_resources import UserResourceRepository
from models.domain.resource import Status, ResourceType
from models.domain.user_resource import UserResource
from models.schemas.user_resource import UserResourceInCreate


@pytest.fixture
def basic_user_resource_request():
    return UserResourceInCreate(userResourceType="user-resource-type", properties={"display_name": "test", "description": "test"})


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
def test_create_user_resource_item_creates_a_user_resource_with_the_right_values(validate_input_mock, user_resource_repo, basic_user_resource_request):
    user_resource_to_create = basic_user_resource_request
    validate_input_mock.return_value = basic_user_resource_request.userResourceType

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
    user_id = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
    user_resource = user_resource_repo.create_user_resource_item(user_resource_to_create, workspace_id, parent_workspace_service_id, user_id)

    assert user_resource.resourceTemplateName == basic_user_resource_request.userResourceType
    assert user_resource.resourceType == ResourceType.UserResource
    assert user_resource.deployment.status == Status.NotDeployed
    assert user_resource.workspaceId == workspace_id
    assert user_resource.parentWorkspaceServiceId == parent_workspace_service_id
    assert user_resource.ownerId == user_id


@patch('db.repositories.user_resources.UserResourceRepository.validate_input_against_template')
def test_create_user_resource_item_raises_value_error_if_template_is_invalid(validate_input_mock, user_resource_repo, basic_user_resource_request):
    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
    user_id = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
    validate_input_mock.side_effect = ValueError

    with pytest.raises(ValueError):
        user_resource_repo.create_user_resource_item(basic_user_resource_request, workspace_id, parent_workspace_service_id, user_id)
