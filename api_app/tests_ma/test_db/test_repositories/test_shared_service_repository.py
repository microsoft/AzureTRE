from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
from mock import patch

from db.errors import DuplicateEntity, EntityDoesNotExist
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.operations import OperationRepository
from models.domain.shared_service import SharedService
from models.domain.resource import ResourceType
from models.schemas.shared_service import SharedServiceInCreate

pytestmark = pytest.mark.asyncio

SHARED_SERVICE_ID = "000000d3-82da-4bfc-b6e9-9a7853ef753e"


@pytest_asyncio.fixture
async def shared_service_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=AsyncMock()):
        shared_service_repo = await SharedServiceRepository().create()
        yield shared_service_repo


@pytest_asyncio.fixture
async def operations_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=None):
        operations_repo = await OperationRepository().create()
        yield operations_repo


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
        templateName="my-shared-service",
        properties={
            "display_name": "test",
            "description": "test",
            "tre_id": "test"
        })


async def test_get_shared_service_by_id_raises_if_does_not_exist(shared_service_repo):
    shared_service_repo.query = AsyncMock(return_value=[])

    with pytest.raises(EntityDoesNotExist):
        await shared_service_repo.get_shared_service_by_id(SHARED_SERVICE_ID)


async def test_get_active_shared_services_for_shared_queries_db(shared_service_repo):
    shared_service_repo.query = AsyncMock(return_value=[])

    await shared_service_repo.get_active_shared_services()

    shared_service_repo.query.assert_called_once_with(query=SharedServiceRepository.active_shared_services_query())


@patch('db.repositories.shared_services.SharedServiceRepository.validate_input_against_template')
@patch('core.config.TRE_ID', "1234")
async def test_create_shared_service_item_creates_a_shared_with_the_right_values(validate_input_mock, shared_service_repo, basic_shared_service_request, basic_shared_service_template):
    shared_service_repo.query = AsyncMock(return_value=[])
    shared_service_to_create = basic_shared_service_request
    validate_input_mock.return_value = basic_shared_service_template

    shared_service, _ = await shared_service_repo.create_shared_service_item(shared_service_to_create, [])

    assert shared_service.templateName == basic_shared_service_request.templateName
    assert shared_service.resourceType == ResourceType.SharedService

    # We expect tre_id to be overriden in the shared service created
    assert shared_service.properties["tre_id"] != shared_service_to_create.properties["tre_id"]
    assert shared_service.properties["tre_id"] == "1234"


@patch('db.repositories.shared_services.SharedServiceRepository.validate_input_against_template')
@patch('core.config.TRE_ID', "1234")
async def test_create_shared_service_item_with_the_same_name_twice_fails(validate_input_mock, shared_service_repo, basic_shared_service_request, basic_shared_service_template):
    shared_service_repo.query = AsyncMock(return_value=[])
    validate_input_mock.return_value = basic_shared_service_template

    shared_service, _ = await shared_service_repo.create_shared_service_item(basic_shared_service_request, [])
    await shared_service_repo.save_item(shared_service)

    shared_service_repo.query = AsyncMock()
    shared_service_repo.query.return_value = [shared_service.__dict__]

    with pytest.raises(DuplicateEntity):
        shared_service = await shared_service_repo.create_shared_service_item(basic_shared_service_request, [])


@patch('db.repositories.shared_services.SharedServiceRepository.validate_input_against_template', side_effect=ValueError)
async def test_create_shared_item_raises_value_error_if_template_is_invalid(_, shared_service_repo, basic_shared_service_request):
    shared_service_repo.query = AsyncMock(return_value=[])
    shared_service_to_create = basic_shared_service_request

    with pytest.raises(ValueError):
        await shared_service_repo.create_shared_service_item(shared_service_to_create, [])
