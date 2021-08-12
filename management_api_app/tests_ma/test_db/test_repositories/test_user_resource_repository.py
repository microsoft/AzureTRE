from jsonschema.exceptions import ValidationError

from mock import patch
import pytest
from db.errors import EntityDoesNotExist
from db.repositories.user_resources import UserResourceRepository
from models.domain.resource import Status, ResourceType
from models.schemas.user_resource import UserResourceInCreate


@pytest.fixture
def basic_user_resource_request():
    return UserResourceInCreate(userResourceType="user-resource-type",
                                properties={"display_name": "test", "description": "test"})


@patch('db.repositories.user_resources.UserResourceRepository._get_current_user_resource_template')
@patch('azure.cosmos.CosmosClient')
def test_create_user_resource_item_creates_a_user_resource_with_the_right_values(cosmos_client_mock,
                                                                                 _get_current_user_resource_template_mock,
                                                                                 basic_user_resource_template,
                                                                                 basic_user_resource_request):
    user_resource_repo = UserResourceRepository(cosmos_client_mock)

    user_resource_to_create = basic_user_resource_request

    resource_template = basic_user_resource_template
    resource_template.required = ["display_name", "description"]

    _get_current_user_resource_template_mock.return_value = basic_user_resource_template.dict()

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
    user_resource = user_resource_repo.create_user_resource_item(user_resource_to_create, workspace_id,
                                                                 parent_workspace_service_id)

    assert user_resource.resourceTemplateName == basic_user_resource_request.userResourceType
    assert user_resource.resourceType == ResourceType.UserResource
    assert user_resource.deployment.status == Status.NotDeployed
    assert user_resource.workspaceId == workspace_id
    assert user_resource.parentWorkspaceServiceId == parent_workspace_service_id


@patch("jsonschema.validate", return_value=None)
@patch('db.repositories.user_resources.UserResourceRepository._get_current_user_resource_template')
@patch('azure.cosmos.CosmosClient')
def test_create_user_resource_item_raises_value_error_if_template_is_invalid(cosmos_client_mock,
                                                                             _get_current_user_resource_template_mock,
                                                                             __):
    user_resource_repo = UserResourceRepository(cosmos_client_mock)

    user_resource_to_create = UserResourceInCreate(
        userResourceType="user-resource-type",
        displayName="my user resource",
        description="some description"
    )

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"

    _get_current_user_resource_template_mock.side_effect = EntityDoesNotExist

    with pytest.raises(ValueError):
        user_resource_repo.create_user_resource_item(user_resource_to_create, workspace_id, parent_workspace_service_id)


@patch('db.repositories.user_resources.UserResourceRepository._get_current_user_resource_template')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_item_does_not_accept_invalid_payload(cosmos_client_mock,
                                                               _get_current_user_resource_template_mock,
                                                               basic_user_resource_template,
                                                               basic_user_resource_request):
    user_resource_repo = UserResourceRepository(cosmos_client_mock)

    user_resource_to_create = basic_user_resource_request
    del user_resource_to_create.properties["display_name"]

    resource_template = basic_user_resource_template
    resource_template.required = ["display_name"]

    _get_current_user_resource_template_mock.return_value = resource_template.dict()

    workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
    parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"

    with pytest.raises(ValidationError) as exc_info:
        user_resource_repo.create_user_resource_item(user_resource_to_create, workspace_id, parent_workspace_service_id)

    assert exc_info.value.message == "'display_name' is a required property"
