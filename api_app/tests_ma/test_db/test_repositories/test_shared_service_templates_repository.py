from mock import patch, MagicMock
import pytest

from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate
from .test_resource_templates_repository import sample_resource_template_as_dict, resource_template_repo
from db.repositories.shared_services import SharedServiceRepository


SHARED_SERVICE_ID = "000000d3-82da-4bfc-b6e9-9a7853ef753e"


@pytest.fixture
def shared_service_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield SharedServiceRepository


def test_get_active_shared_services_for_shared_queries_db(shared_service_repo):
    shared_service_repo.query = MagicMock()
    shared_service_repo.query.return_value = []

    shared_service_repo.get_active_shared_services(SHARED_SERVICE_ID)

    shared_service_repo.query.assert_called_once_with(query=SharedServiceRepository.active_shared_services_query(SHARED_SERVICE_ID))


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
