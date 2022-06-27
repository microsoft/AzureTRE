from fastapi import HTTPException
from mock import patch, MagicMock
import pytest
from tests_ma.test_api.conftest import create_test_user
from models.schemas.airlock_request import AirlockRequestInCreate
from models.domain.airlock_resource import AirlockResourceType
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from db.repositories.airlock_requests import AirlockRequestRepository

from db.errors import EntityDoesNotExist
from azure.cosmos.exceptions import CosmosResourceNotFoundError


WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "ce45d43a-e734-469a-88a0-109faf4a611f"
DRAFT = AirlockRequestStatus.Draft
SUBMITTED = AirlockRequestStatus.Submitted
IN_REVIEW = AirlockRequestStatus.InReview
APPROVED_IN_PROGRESS = AirlockRequestStatus.ApprovalInProgress
APPROVED = AirlockRequestStatus.Approved
REJECTION_IN_PROGRESS = AirlockRequestStatus.RejectionInProgress
REJECTED = AirlockRequestStatus.Rejected
CANCELLED = AirlockRequestStatus.Cancelled
BLOCKING_IN_PROGRESS = AirlockRequestStatus.Blocked
BLOCKED = AirlockRequestStatus.Blocked


@pytest.fixture
def airlock_request_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield AirlockRequestRepository(cosmos_client_mock)


@pytest.fixture
def sample_airlock_request_input():
    return AirlockRequestInCreate(requestType=AirlockRequestType.Import, businessJustification="Some business justification")


def airlock_request_mock(status=AirlockRequestStatus.Draft):
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        resourceType=AirlockResourceType.AirlockRequest,
        workspaceId=WORKSPACE_ID,
        requestType=AirlockRequestType.Import,
        files=[],
        businessJustification="some test reason",
        status=status
    )
    return airlock_request


def test_get_airlock_request_by_id(airlock_request_repo):
    airlock_request = airlock_request_mock()
    airlock_request_repo.read_item_by_id = MagicMock(return_value=airlock_request)
    actual_service = airlock_request_repo.get_airlock_request_by_id(AIRLOCK_REQUEST_ID)

    assert actual_service == airlock_request


def test_get_airlock_request_by_id_raises_entity_does_not_exist_if_no_such_request_id(airlock_request_repo):
    airlock_request_repo.read_item_by_id = MagicMock()
    airlock_request_repo.read_item_by_id.side_effect = CosmosResourceNotFoundError

    with pytest.raises(EntityDoesNotExist):
        airlock_request_repo.get_airlock_request_by_id(AIRLOCK_REQUEST_ID)


def test_create_airlock_request_item_creates_an_airlock_request_with_the_right_values(sample_airlock_request_input, airlock_request_repo):
    airlock_request_item_to_create = sample_airlock_request_input
    airlock_request = airlock_request_repo.create_airlock_request_item(airlock_request_item_to_create, WORKSPACE_ID)

    assert airlock_request.resourceType == AirlockResourceType.AirlockRequest
    assert airlock_request.workspaceId == WORKSPACE_ID


@pytest.mark.parametrize("airlock_request_repo, current_status, new_status", [(airlock_request_repo, DRAFT, SUBMITTED), (airlock_request_repo, SUBMITTED, IN_REVIEW), (airlock_request_repo, SUBMITTED, BLOCKING_IN_PROGRESS), (airlock_request_repo, IN_REVIEW, APPROVED_IN_PROGRESS), (airlock_request_repo, IN_REVIEW, REJECTION_IN_PROGRESS), (airlock_request_repo, REJECTION_IN_PROGRESS, REJECTED), (airlock_request_repo, APPROVED_IN_PROGRESS, APPROVED), (airlock_request_repo, BLOCKING_IN_PROGRESS, BLOCKED), (airlock_request_repo, DRAFT, CANCELLED), (airlock_request_repo, IN_REVIEW, CANCELLED)], indirect=['airlock_request_repo'])
def test_update_airlock_request_status_updates_airlock_request_with_the_right_status(airlock_request_repo, current_status, new_status):
    airlock_request_item_to_create = airlock_request_mock(status=current_status)
    user = create_test_user()
    airlock_request = airlock_request_repo.update_airlock_request_status(airlock_request_item_to_create, new_status, user)

    assert airlock_request.status == new_status

# Todo: Create the matrix of all forbidden status changes...

@pytest.mark.parametrize("airlock_request_repo, current_status, new_status", [(airlock_request_repo, BLOCKED, APPROVED), (airlock_request_repo, APPROVED, IN_REVIEW), (airlock_request_repo, REJECTED, APPROVED), (airlock_request_repo, APPROVED, REJECTED), (airlock_request_repo, DRAFT, IN_REVIEW), (airlock_request_repo, SUBMITTED, APPROVED), (airlock_request_repo, IN_REVIEW, SUBMITTED), (airlock_request_repo, BLOCKED, APPROVED)], indirect=['airlock_request_repo'])
def test_update_airlock_request_status_fails_on_validation_wrong_status(airlock_request_repo, current_status, new_status):
    airlock_request_item_to_create = airlock_request_mock(status=current_status)
    user = create_test_user()
    with pytest.raises(HTTPException):
        airlock_request_repo.update_airlock_request_status(airlock_request_item_to_create, new_status, user)
