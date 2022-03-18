import pytest
from mock import patch

from db.repositories.resource_templates import ResourceTemplateRepository
from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from .test_resource_templates_repository import sample_resource_template_as_dict


@pytest.fixture
def resource_template_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield ResourceTemplateRepository(cosmos_client_mock)


# Because shared service templates repository uses generic ResourceTemplate repository, most test cases are already covered
@patch('db.repositories.resource_templates.ResourceTemplateRepository.save_item')
@patch('uuid.uuid4')
def test_create_shared_service_template_item_calls_create_item_with_the_correct_parameters(uuid_mock, save_item_mock, resource_template_repo, input_shared_service_template):
    uuid_mock.return_value = "1234"

    returned_template = resource_template_repo.create_template(input_shared_service_template, ResourceType.SharedService)

    expected_resource_template = ResourceTemplate(
        id="1234",
        name=input_shared_service_template.name,
        title=input_shared_service_template.json_schema["title"],
        description=input_shared_service_template.json_schema["description"],
        version=input_shared_service_template.version,
        resourceType=ResourceType.SharedService,
        properties=input_shared_service_template.json_schema["properties"],
        actions=input_shared_service_template.customActions,
        required=input_shared_service_template.json_schema["required"],
        current=input_shared_service_template.current,
    )
    save_item_mock.assert_called_once_with(expected_resource_template)
    assert expected_resource_template == returned_template


@patch('db.repositories.resource_templates.ResourceTemplateRepository.query')
def test_get_templates_for_shared_services_queries_db(query_mock, resource_template_repo):
    expected_query = 'SELECT c.name, c.title, c.description FROM c WHERE c.resourceType = "shared-service" AND c.current = true'
    query_mock.return_value = [sample_resource_template_as_dict(name="test", version="1.0", resource_type=ResourceType.SharedService)]

    resource_template_repo.get_templates_information(ResourceType.SharedService, parent_service_name="parent_service")

    query_mock.assert_called_once_with(query=expected_query)
