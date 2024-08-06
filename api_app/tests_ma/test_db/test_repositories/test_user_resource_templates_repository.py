import pytest
import pytest_asyncio
from mock import patch

from db.errors import DuplicateEntity, EntityDoesNotExist
from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.domain.user_resource_template import UserResourceTemplate


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def resource_template_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        resource_template_repo = await ResourceTemplateRepository().create()
        yield resource_template_repo


def sample_user_resource_template_as_dict(name: str, version: str = "1.0") -> dict:
    template = UserResourceTemplate(
        id="123",
        name=name,
        description="",
        version=version,
        current=True,
        required=[],
        authorizedRoles=[],
        properties={},
        customActions=[],
        parentWorkspaceService="parent_service")
    return template.dict()


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_user_resource_template_by_name_and_version_queries_db(query_mock, resource_template_repo):
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "user-resource" AND c.name = "test" AND c.version = "1.0" AND c.parentWorkspaceService = "parent_service"'
    query_mock.return_value = [sample_user_resource_template_as_dict(name="test", version="1.0")]

    await resource_template_repo.get_template_by_name_and_version(name="test", version="1.0", resource_type=ResourceType.UserResource, parent_service_name="parent_service")

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_current_user_resource_template_queries_db(query_mock, resource_template_repo):
    template_name = "template1"
    parent_template_name = "parent_template1"
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "user-resource" AND c.name = "template1" AND c.current = true AND c.parentWorkspaceService = "parent_template1"'
    query_mock.return_value = [sample_user_resource_template_as_dict(name=template_name)]

    await resource_template_repo.get_current_template(template_name, ResourceType.UserResource, parent_template_name)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_current_user_resource_template_returns_matching_template(query_mock, resource_template_repo):
    template_name = "template1"
    parent_template_name = "parent_template1"
    query_mock.return_value = [sample_user_resource_template_as_dict(name=template_name)]

    template = await resource_template_repo.get_current_template(template_name, ResourceType.UserResource, parent_template_name)

    assert template.name == template_name


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_current_user_resource_template_raises_entity_does_not_exist_if_no_template_found(query_mock, resource_template_repo):
    query_mock.return_value = []

    with pytest.raises(EntityDoesNotExist):
        await resource_template_repo.get_current_template("template1", ResourceType.UserResource, "parent_template1")


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_current_user_resource_template_raises_duplicate_entity_if_multiple_current_found(query_mock, resource_template_repo):
    template_name = "template1"
    parent_template_name = "parent_template1"
    query_mock.return_value = [sample_user_resource_template_as_dict(name=template_name), sample_user_resource_template_as_dict(name=template_name)]

    with pytest.raises(DuplicateEntity):
        await resource_template_repo.get_current_template(template_name, ResourceType.UserResource, parent_template_name)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
async def test_create_user_resource_template_item_calls_create_item_with_the_correct_parameters(uuid_mock, save_item_mock, resource_template_repo, input_user_resource_template):
    uuid_mock.return_value = "1234"

    returned_template = await resource_template_repo.create_template(input_user_resource_template, ResourceType.UserResource, "parent_service_template_name")

    expected_resource_template = UserResourceTemplate(
        id="1234",
        name=input_user_resource_template.name,
        title=input_user_resource_template.json_schema["title"],
        description=input_user_resource_template.json_schema["description"],
        version=input_user_resource_template.version,
        resourceType=ResourceType.UserResource,
        properties=input_user_resource_template.json_schema["properties"],
        customActions=input_user_resource_template.customActions,
        required=input_user_resource_template.json_schema["required"],
        current=input_user_resource_template.current,
        parentWorkspaceService="parent_service_template_name"
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
async def test_get_template_infos_for_user_resources_queries_db(query_mock, resource_template_repo):
    expected_query = 'SELECT c.name, c.title, c.description, c.authorizedRoles FROM c WHERE c.resourceType = "user-resource" AND c.current = true AND c.parentWorkspaceService = "parent_service"'
    query_mock.return_value = [sample_user_resource_template_as_dict(name="test", version="1.0")]

    await resource_template_repo.get_templates_information(ResourceType.UserResource, parent_service_name="parent_service")

    query_mock.assert_called_once_with(query=expected_query)
