from fastapi import HTTPException
from mock import patch, MagicMock
import pytest
from tests_ma.test_api.conftest import create_test_user
from models.schemas.airlock_request import AirlockRequestInCreate
from models.domain.airlock_resource import AirlockResourceType
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from db.repositories.airlock_requests import AirlockRequestRepository

from db.errors import EntityDoesNotExist


WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "ce45d43a-e734-469a-88a0-109faf4a611f"


@pytest.fixture
def airlock_request_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield AirlockRequestRepository(cosmos_client_mock)


@pytest.fixture
def airlock_request_mock():
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        resourceType=AirlockResourceType.AirlockRequest,
        workspaceId=WORKSPACE_ID,
        requestType=AirlockRequestType.Import,
        files=[],
        businessJustification="some test reason"
    )
    return airlock_request


@pytest.fixture
def sample_airlock_request_input():
    return AirlockRequestInCreate(requestType=AirlockRequestType.Import, businessJustification="Some business justification")


def test_get_airlock_request_by_id(airlock_request_repo, airlock_request_mock):
    airlock_request = airlock_request_mock
    airlock_request_repo.read_item_by_id = MagicMock(return_value=airlock_request_mock)
    actual_service = airlock_request_repo.get_airlock_request_by_id(AIRLOCK_REQUEST_ID)

    assert actual_service == airlock_request


def test_get_airlock_request_by_id_raises_entity_does_not_exist_if_no_available_services(airlock_request_repo):
    airlock_request_repo.read_item_by_id = MagicMock()
    airlock_request_repo.read_item_by_id.return_value = []

    with pytest.raises(EntityDoesNotExist):
        airlock_request_repo.get_airlock_request_by_id(AIRLOCK_REQUEST_ID)


def test_create_airlock_request_item_creates_an_airlock_request_with_the_right_values(sample_airlock_request_input, airlock_request_repo):
    airlock_request_item_to_create = sample_airlock_request_input
    airlock_request = airlock_request_repo.create_airlock_request_item(airlock_request_item_to_create, WORKSPACE_ID)

    assert airlock_request.resourceType == AirlockResourceType.AirlockRequest
    assert airlock_request.workspaceId == WORKSPACE_ID


def test_update_airlock_request_status_updates_airlock_request_with_the_right_status(airlock_request_mock, airlock_request_repo):
    airlock_request_item_to_create = airlock_request_mock
    new_status = AirlockRequestStatus.Submitted
    user = create_test_user()
    airlock_request = airlock_request_repo.update_airlock_request_status(airlock_request_item_to_create, new_status, user)

    assert airlock_request.status == new_status


def test_update_airlock_request_status_fails_on_validation_wrong_status(airlock_request_mock, airlock_request_repo):
    airlock_request_item_to_create = airlock_request_mock
    new_status = AirlockRequestStatus.Approved
    user = create_test_user()
    with pytest.raises(HTTPException):
        airlock_request_repo.update_airlock_request_status(airlock_request_item_to_create, new_status, user)
