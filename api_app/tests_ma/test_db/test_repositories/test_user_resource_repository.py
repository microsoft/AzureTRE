from mock import patch
import pytest
import pytest_asyncio

from db.errors import EntityDoesNotExist
from db.repositories.resources import IS_NOT_DELETED_CLAUSE
from db.repositories.user_resources import UserResourceRepository
from models.domain.resource import ResourceType
from models.domain.user_resource import UserResource
from models.schemas.user_resource import UserResourceInCreate


WORKSPACE_ID = "def000d3-82da-4bfc-b6e9-9a7853ef753e"
SERVICE_ID = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
RESOURCE_ID = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
USER_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"


pytestmark = pytest.mark.asyncio


@pytest.fixture
def basic_user_resource_request():
    return UserResourceInCreate(templateName="user-resource-type", properties={"display_name": "test", "description": "test", "tre_id": "test"})


@pytest_asyncio.fixture
async def user_resource_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        user_resource_repo = await UserResourceRepository().create()
        yield user_resource_repo


@pytest.fixture
def user_resource():
    user_resource = UserResource(
        id=RESOURCE_ID,
        templateVersion="0.1.0",
        properties={},
        etag='',
        templateName="my-user-resource",
        resourcePath="test"
    )
    return user_resource


@patch('db.repositories.user_resources.UserResourceRepository.validate_input_against_template')
@patch('core.config.TRE_ID', "9876")
async def test_create_user_resource_item_creates_a_user_resource_with_the_right_values(validate_input_mock, user_resource_repo, basic_user_resource_request, basic_user_resource_template):
    user_resource_to_create = basic_user_resource_request
    validate_input_mock.return_value = basic_user_resource_template

    user_resource, _ = await user_resource_repo.create_user_resource_item(user_resource_to_create, WORKSPACE_ID, SERVICE_ID, "parent-service-type", USER_ID, [])

    assert user_resource.templateName == basic_user_resource_request.templateName
    assert user_resource.resourceType == ResourceType.UserResource
    assert user_resource.workspaceId == WORKSPACE_ID
    assert user_resource.parentWorkspaceServiceId == SERVICE_ID
    assert user_resource.ownerId == USER_ID
    assert len(user_resource.properties["tre_id"]) > 0
    # need to make sure request doesn't override system param
    assert user_resource.properties["tre_id"] != "test"


@patch('db.repositories.user_resources.UserResourceRepository.validate_input_against_template', side_effect=ValueError)
async def test_create_user_resource_item_raises_value_error_if_template_is_invalid(_, user_resource_repo, basic_user_resource_request):
    with pytest.raises(ValueError):
        await user_resource_repo.create_user_resource_item(basic_user_resource_request, WORKSPACE_ID, SERVICE_ID, "parent-service-type", USER_ID, [])


@patch('db.repositories.user_resources.UserResourceRepository.query', return_value=[])
async def test_get_user_resources_for_workspace_queries_db(query_mock, user_resource_repo):
    expected_query = f'SELECT * FROM c WHERE {IS_NOT_DELETED_CLAUSE} AND c.resourceType = "user-resource" AND c.parentWorkspaceServiceId = "{SERVICE_ID}" AND c.workspaceId = "{WORKSPACE_ID}"'

    await user_resource_repo.get_user_resources_for_workspace_service(WORKSPACE_ID, SERVICE_ID)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.user_resources.UserResourceRepository.query')
async def test_get_user_resource_returns_resource_if_found(query_mock, user_resource_repo, user_resource):
    query_mock.return_value = [user_resource.dict()]

    actual_resource = await user_resource_repo.get_user_resource_by_id(WORKSPACE_ID, SERVICE_ID, RESOURCE_ID)

    assert actual_resource == user_resource


@patch('db.repositories.user_resources.UserResourceRepository.query')
async def test_get_user_resource_by_id_queries_db(query_mock, user_resource_repo, user_resource):
    query_mock.return_value = [user_resource.dict()]
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "user-resource" AND c.parentWorkspaceServiceId = "{SERVICE_ID}" AND c.workspaceId = "{WORKSPACE_ID}" AND c.id = "{RESOURCE_ID}"'

    await user_resource_repo.get_user_resource_by_id(WORKSPACE_ID, SERVICE_ID, RESOURCE_ID)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.user_resources.UserResourceRepository.query', return_value=[])
async def test_get_user_resource_by_id_raises_entity_does_not_exist_if_not_found(_, user_resource_repo):
    with pytest.raises(EntityDoesNotExist):
        await user_resource_repo.get_user_resource_by_id(WORKSPACE_ID, SERVICE_ID, RESOURCE_ID)
