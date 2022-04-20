
import pytest
from mock import patch, MagicMock

from db.errors import EntityDoesNotExist, ResourceIsNotDeployed
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.operations import OperationRepository
from models.domain.shared_service import SharedService
from models.domain.resource import ResourceType
from models.schemas.shared_service import SharedServiceInCreate


SHARED_SERVICE_ID = "000000d3-82da-4bfc-b6e9-9a7853ef753e"


@pytest.fixture
def shared_service_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield SharedServiceRepository(cosmos_client_mock)


@pytest.fixture
def operations_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield OperationRepository(cosmos_client_mock)


@pytest.fixture
def shared_service():
    shared_service = SharedService(
        id=SHARED_SERVICE_ID,
        templateVersion="0.1.0",
        etag='',
        properties={},
        templateName="my-shared-service",
        resourcePath="test"
    )
    return shared_service


@pytest.fixture
def basic_shared_service_request():
    return SharedServiceInCreate(
        templateName="shared-service-type",
        properties={
            "display_name": "test",
            "description": "test",
            "tre_id": "test"
        })


def test_get_shared_service_by_id_returns_resource(shared_service_repo, shared_service, operations_repo):
    service = shared_service

    shared_service_repo.get_shared_service_by_id = MagicMock(return_value=service)
    operations_repo.resource_has_deployed_operation = MagicMock(return_value=True)

    actual_service = shared_service_repo.get_deployed_shared_service_by_id(SHARED_SERVICE_ID, operations_repo)

    assert actual_service == service


def test_get_shared_service_by_id_raises_if_does_not_exist(shared_service_repo):
    shared_service_repo.query = MagicMock()
    shared_service_repo.query.return_value = []

    with pytest.raises(EntityDoesNotExist):
        shared_service_repo.get_shared_service_by_id(SHARED_SERVICE_ID)


def test_get_shared_service_by_id_raises_resource_is_not_deployed(shared_service_repo, shared_service, operations_repo):
    service = shared_service

    shared_service_repo.get_shared_service_by_id = MagicMock(return_value=service)
    operations_repo.resource_has_deployed_operation = MagicMock(return_value=False)

    with pytest.raises(ResourceIsNotDeployed):
        shared_service_repo.get_deployed_shared_service_by_id(SHARED_SERVICE_ID, operations_repo)


def test_get_active_shared_services_for_shared_queries_db(shared_service_repo):
    shared_service_repo.query = MagicMock()
    shared_service_repo.query.return_value = []

    shared_service_repo.get_active_shared_services()

    shared_service_repo.query.assert_called_once_with(query=SharedServiceRepository.active_shared_services_query())


@patch('db.repositories.shared_services.SharedServiceRepository.validate_input_against_template')
@patch('core.config.TRE_ID', "1234")
def test_create_shared_service_item_creates_a_shared_with_the_right_values(validate_input_mock, shared_service_repo, basic_shared_service_request, basic_shared_service_template):
    shared_service_to_create = basic_shared_service_request

    resource_template = basic_shared_service_template
    resource_template.required = ["display_name", "description"]

    validate_input_mock.return_value = basic_shared_service_request.templateName

    shared_service = shared_service_repo.create_shared_service_item(shared_service_to_create)

    assert shared_service.templateName == basic_shared_service_request.templateName
    assert shared_service.resourceType == ResourceType.SharedService

    # We expect tre_id to be overriden in the shared service created
    assert shared_service.properties["tre_id"] != shared_service_to_create.properties["tre_id"]
    assert shared_service.properties["tre_id"] == "1234"


@patch('db.repositories.shared_services.SharedServiceRepository.validate_input_against_template', side_effect=ValueError)
def test_create_shared_item_raises_value_error_if_template_is_invalid(_, shared_service_repo, basic_shared_service_request):
    shared_service_to_create = basic_shared_service_request

    with pytest.raises(ValueError):
        shared_service_repo.create_shared_service_item(shared_service_to_create)
