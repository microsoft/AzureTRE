from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from mock import patch
import pytest
import pytest_asyncio
from tests_ma.test_api.conftest import create_test_user
from models.schemas.airlock_request import AirlockRequestInCreate
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from db.repositories.airlock_requests import AirlockRequestRepository

from db.errors import EntityDoesNotExist
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosAccessConditionFailedError

pytestmark = pytest.mark.asyncio

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
BLOCKING_IN_PROGRESS = AirlockRequestStatus.BlockingInProgress
BLOCKED = AirlockRequestStatus.Blocked
FAILED = AirlockRequestStatus.Failed

ALL_STATUSES = [enum.value for enum in AirlockRequestStatus]

ALLOWED_STATUS_CHANGES = {
    DRAFT: [SUBMITTED, CANCELLED, FAILED],
    SUBMITTED: [IN_REVIEW, BLOCKING_IN_PROGRESS, FAILED],
    IN_REVIEW: [APPROVED_IN_PROGRESS, REJECTION_IN_PROGRESS, CANCELLED, FAILED],
    APPROVED_IN_PROGRESS: [APPROVED, FAILED],
    APPROVED: [],
    REJECTION_IN_PROGRESS: [REJECTED, FAILED],
    REJECTED: [],
    CANCELLED: [],
    BLOCKING_IN_PROGRESS: [BLOCKED, FAILED],
    BLOCKED: [],
    FAILED: [],
}


@pytest_asyncio.fixture
async def airlock_request_repo():
    with patch('api.dependencies.database.Database.get_container_proxy', return_value=AsyncMock()):
        airlock_request_repo_mock = await AirlockRequestRepository.create()
        yield airlock_request_repo_mock


@pytest.fixture
def sample_airlock_request_input():
    return AirlockRequestInCreate(type=AirlockRequestType.Import, businessJustification="Some business justification")


@pytest.fixture
def verify_dictionary_contains_all_enum_values():
    for status in ALL_STATUSES:
        if status not in ALLOWED_STATUS_CHANGES:
            raise Exception(f"Status '{status}' was not added to the ALLOWED_STATUS_CHANGES dictionary")


def airlock_request_mock(status=AirlockRequestStatus.Draft):
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        workspaceId=WORKSPACE_ID,
        type=AirlockRequestType.Import,
        files=[],
        businessJustification="some test reason",
        status=status,
        reviews=[]

    )
    return airlock_request


def get_allowed_status_changes():
    for current_status, allowed_new_statuses in ALLOWED_STATUS_CHANGES.items():
        for new_status in allowed_new_statuses:
            yield current_status, new_status


def get_forbidden_status_changes():
    for current_status, allowed_new_statuses in ALLOWED_STATUS_CHANGES.items():
        forbidden_new_statuses = list(set(ALL_STATUSES) - set(allowed_new_statuses))
        for new_status in forbidden_new_statuses:
            yield current_status, new_status


async def test_get_airlock_request_by_id(airlock_request_repo):
    airlock_request = airlock_request_mock()
    airlock_request_repo.read_item_by_id = AsyncMock(return_value=airlock_request)
    actual_service = await airlock_request_repo.get_airlock_request_by_id(AIRLOCK_REQUEST_ID)

    assert actual_service == airlock_request


async def test_get_airlock_request_by_id_raises_entity_does_not_exist_if_no_such_request_id(airlock_request_repo):
    airlock_request_repo.read_item_by_id = AsyncMock()
    airlock_request_repo.read_item_by_id.side_effect = CosmosResourceNotFoundError

    with pytest.raises(EntityDoesNotExist):
        await airlock_request_repo.get_airlock_request_by_id(AIRLOCK_REQUEST_ID)


async def test_create_airlock_request_item_creates_an_airlock_request_with_the_right_values(sample_airlock_request_input, airlock_request_repo):
    airlock_request_item_to_create = sample_airlock_request_input
    created_by_user = {'id': 'test_user_id'}
    airlock_request = airlock_request_repo.create_airlock_request_item(airlock_request_item_to_create, WORKSPACE_ID, created_by_user)

    assert airlock_request.workspaceId == WORKSPACE_ID
    assert airlock_request.createdBy['id'] == 'test_user_id'


@pytest.mark.parametrize("current_status, new_status", get_allowed_status_changes())
async def test_update_airlock_request_with_allowed_new_status_should_update_request_status(airlock_request_repo, current_status, new_status, verify_dictionary_contains_all_enum_values):
    user = create_test_user()
    mock_existing_request = airlock_request_mock(status=current_status)
    airlock_request = await airlock_request_repo.update_airlock_request(mock_existing_request, user, new_status)
    assert airlock_request.status == new_status


@pytest.mark.parametrize("current_status, new_status", get_forbidden_status_changes())
async def test_update_airlock_request_with_forbidden_status_should_fail_on_validation(airlock_request_repo, current_status, new_status, verify_dictionary_contains_all_enum_values):
    user = create_test_user()
    mock_existing_request = airlock_request_mock(status=current_status)
    with pytest.raises(HTTPException):
        await airlock_request_repo.update_airlock_request(mock_existing_request, user, new_status)


@patch("db.repositories.airlock_requests.AirlockRequestRepository.update_airlock_request_item", side_effect=[CosmosAccessConditionFailedError, None])
@patch("db.repositories.airlock_requests.AirlockRequestRepository.get_airlock_request_by_id", return_value=airlock_request_mock(status=DRAFT))
async def test_update_airlock_request_should_retry_update_when_etag_is_not_up_to_date(_, update_airlock_request_item_mock, airlock_request_repo):
    expected_update_attempts = 2
    user = create_test_user()
    mock_existing_request = airlock_request_mock(status=DRAFT)
    await airlock_request_repo.update_airlock_request(original_request=mock_existing_request, updated_by=user, new_status=SUBMITTED)
    assert update_airlock_request_item_mock.call_count == expected_update_attempts


async def test_get_airlock_requests_queries_db(airlock_request_repo):
    airlock_request_repo.container.query_items = MagicMock()
    expected_query = airlock_request_repo.airlock_requests_query() + f' WHERE c.workspaceId = "{WORKSPACE_ID}"'
    expected_parameters = [
        {"name": "@user_id", "value": None},
        {"name": "@status", "value": None},
        {"name": "@type", "value": None},
    ]

    await airlock_request_repo.get_airlock_requests(WORKSPACE_ID)
    airlock_request_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=expected_parameters)
