import pytest
from mock import patch

from db.repositories.resource_templates import ResourceTemplateRepository
from db.errors import EntityDoesNotExist
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate


def sample_resource_template(name: str, version: str = "1.0", resource_type: ResourceType = ResourceType.Workspace) -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=name,
        description="test",
        version=version,
        resourceType=resource_type,
        current=False,
        properties={},
        required=[],
    )


def sample_resource_template_as_dict(name: str, version: str = "1.0", resource_type: ResourceType = ResourceType.Workspace) -> dict:
    return sample_resource_template(name, version, resource_type).dict()


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_queries_db(cosmos_client_mock, query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test" AND c.version = "1.0"'
    query_mock.return_value = [sample_resource_template_as_dict(name="test", version="1.0")]

    template_repo.get_template_by_name_and_version(name="test", version="1.0", resource_type=ResourceType.Workspace)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_returns_matching_template(cosmos_client_mock, query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    template_version = "1.0"
    workspace_templates_in_db = [sample_resource_template_as_dict(name=template_name, version=template_version)]
    query_mock.return_value = workspace_templates_in_db

    template = template_repo.get_template_by_name_and_version(name=template_name, version=template_version, resource_type=ResourceType.Workspace)

    assert template.name == template_name


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_by_name_and_version_raises_entity_does_not_exist_if_no_template_found(cosmos_client_mock, query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    template_version = "1.0"
    query_mock.return_value = []

    with pytest.raises(EntityDoesNotExist):
        template_repo.get_template_by_name_and_version(name=template_name, version=template_version, resource_type=ResourceType.Workspace)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_current_by_name_queries_db(cosmos_client_mock, query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT * FROM c WHERE c.resourceType = "workspace" AND c.name = "test" AND c.current = true'
    query_mock.return_value = [sample_resource_template_as_dict(name="test")]

    template_repo.get_current_template(template_name="test", resource_type=ResourceType.Workspace)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_current_by_name_returns_matching_template(cosmos_client_mock, query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    template_name = "test"
    query_mock.return_value = [sample_resource_template_as_dict(name=template_name)]

    template = template_repo.get_current_template(template_name=template_name, resource_type=ResourceType.Workspace)

    assert template.name == template_name


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_current_by_name_raises_entity_does_not_exist_if_no_template_found(cosmos_client_mock, query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    query_mock.return_value = []

    with pytest.raises(EntityDoesNotExist):
        template_repo.get_current_template(template_name="test", resource_type=ResourceType.Workspace)


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_templates_information_returns_unique_template_names(cosmos_client_mock, query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    query_mock.return_value = [
        {"name": "template1", "description": "description1"},
        {"name": "template2", "description": "description2"}
    ]

    result = template_repo.get_templates_information(ResourceType.Workspace)

    assert len(result) == 2
    assert result[0].name == "template1"
    assert result[1].name == "template2"


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
@patch('azure.cosmos.CosmosClient')
def test_create_workspace_template_item_calls_create_item_with_the_correct_parameters(cosmos_mock, uuid_mock, save_item_mock, input_workspace_template):
    template_repo = ResourceTemplateRepository(cosmos_mock)
    uuid_mock.return_value = "1234"

    returned_template = template_repo.create_template(input_workspace_template, ResourceType.Workspace)

    expected_resource_template = ResourceTemplate(
        id="1234",
        name=input_workspace_template.name,
        description=input_workspace_template.json_schema["description"],
        version=input_workspace_template.version,
        resourceType=ResourceType.Workspace,
        properties=input_workspace_template.json_schema["properties"],
        required=input_workspace_template.json_schema["required"],
        current=input_workspace_template.current
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
@patch('azure.cosmos.CosmosClient')
def test_create_item_created_with_the_expected_type(cosmos_mock, uuid_mock, save_item_mock, input_workspace_template):
    template_repo = ResourceTemplateRepository(cosmos_mock)
    uuid_mock.return_value = "1234"
    expected_type = ResourceType.WorkspaceService
    returned_template = template_repo.create_template(input_workspace_template, expected_type)
    expected_resource_template = ResourceTemplate(
        id="1234",
        name=input_workspace_template.name,
        description=input_workspace_template.json_schema["description"],
        version=input_workspace_template.version,
        resourceType=expected_type,
        properties=input_workspace_template.json_schema["properties"],
        required=input_workspace_template.json_schema["required"],
        current=input_workspace_template.current
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.resource_templates.ResourceTemplateRepository.update_item')
@patch('azure.cosmos.CosmosClient')
def test_update_item_calls_upsert_with_correct_parameters(cosmos_mock, update_mock):
    template_repo = ResourceTemplateRepository(cosmos_mock)
    resource_template = sample_resource_template("blah", "blah")

    template_repo.update_item(resource_template)

    update_mock.assert_called_once_with(resource_template.dict())


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
@patch('azure.cosmos.CosmosClient')
def test_get_template_infos_for_user_resources_queries_db(cosmos_client_mock, wt_query_mock):
    template_repo = ResourceTemplateRepository(cosmos_client_mock)
    expected_query = 'SELECT c.name, c.description FROM c WHERE c.resourceType = "user-resource" AND c.current = true AND c.parentWorkspaceService = "parent_service"'
    wt_query_mock.return_value = [sample_resource_template_as_dict(name="test", version="1.0", resource_type=ResourceType.UserResource)]

    template_repo.get_templates_information(ResourceType.UserResource, parent_service_name="parent_service")

    wt_query_mock.assert_called_once_with(query=expected_query)
