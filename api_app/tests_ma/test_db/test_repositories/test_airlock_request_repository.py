from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from mock import patch
import pytest
import pytest_asyncio
from models.domain.authentication import RoleAssignment, User
from models.domain.workspace import Workspace
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
REVOKED = AirlockRequestStatus.Revoked

ALL_STATUSES = [enum.value for enum in AirlockRequestStatus]

ALLOWED_STATUS_CHANGES = {
    DRAFT: [SUBMITTED, CANCELLED, FAILED],
    SUBMITTED: [IN_REVIEW, BLOCKING_IN_PROGRESS, FAILED],
    IN_REVIEW: [APPROVED_IN_PROGRESS, REJECTION_IN_PROGRESS, CANCELLED, FAILED],
    APPROVED_IN_PROGRESS: [APPROVED, FAILED],
    APPROVED: [REVOKED],
    REJECTION_IN_PROGRESS: [REJECTED, FAILED],
    REJECTED: [],
    CANCELLED: [],
    BLOCKING_IN_PROGRESS: [BLOCKED, FAILED],
    BLOCKED: [],
    FAILED: [],
    REVOKED: [],
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


def sample_workspace(workspace_id=WORKSPACE_ID, workspace_properties: dict = {}) -> Workspace:
    workspace = Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties=workspace_properties,
        resourcePath=f'/workspaces/{workspace_id}'
    )
    return workspace


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
    expected_query = airlock_request_repo.airlock_requests_query() + ' WHERE c.workspaceId=@workspace_id'
    expected_parameters = [
        {"name": "@workspace_id", "value": WORKSPACE_ID},
    ]

    await airlock_request_repo.get_airlock_requests(WORKSPACE_ID)
    airlock_request_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=expected_parameters)


async def test_get_airlock_requests_with_user_id(airlock_request_repo):
    airlock_request_repo.container.query_items = MagicMock()
    user_id = "test_user_id"
    expected_query = airlock_request_repo.airlock_requests_query() + ' WHERE c.createdBy.id=@user_id'
    expected_parameters = [
        {"name": "@user_id", "value": user_id},
    ]

    await airlock_request_repo.get_airlock_requests(creator_user_id=user_id)
    airlock_request_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=expected_parameters)


async def test_get_airlock_requests_with_status(airlock_request_repo):
    airlock_request_repo.container.query_items = MagicMock()
    status = AirlockRequestStatus.Submitted
    expected_query = airlock_request_repo.airlock_requests_query() + ' WHERE c.status=@status'
    expected_parameters = [
        {"name": "@status", "value": status}
    ]

    await airlock_request_repo.get_airlock_requests(status=status)
    airlock_request_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=expected_parameters)


async def test_get_airlock_requests_with_type(airlock_request_repo):
    airlock_request_repo.container.query_items = MagicMock()
    request_type = AirlockRequestType.Import
    expected_query = airlock_request_repo.airlock_requests_query() + ' WHERE c.type=@type'
    expected_parameters = [
        {"name": "@type", "value": request_type},
    ]

    await airlock_request_repo.get_airlock_requests(type=request_type)
    airlock_request_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=expected_parameters)


async def test_get_airlock_requests_with_multiple_filters(airlock_request_repo):
    airlock_request_repo.container.query_items = MagicMock()
    user_id = "test_user_id"
    status = AirlockRequestStatus.Submitted
    request_type = AirlockRequestType.Import
    expected_query = airlock_request_repo.airlock_requests_query() + ' WHERE c.createdBy.id=@user_id AND c.status=@status AND c.type=@type'
    expected_parameters = [
        {"name": "@user_id", "value": user_id},
        {"name": "@status", "value": status},
        {"name": "@type", "value": request_type},
    ]

    await airlock_request_repo.get_airlock_requests(creator_user_id=user_id, status=status, type=request_type)
    airlock_request_repo.container.query_items.assert_called_once_with(query=expected_query, parameters=expected_parameters)


@pytest.mark.asyncio
@patch.object(AirlockRequestRepository, 'get_airlock_requests', new_callable=AsyncMock)
@patch('db.repositories.airlock_requests.get_access_service', autospec=True)
@patch('db.repositories.airlock_requests.WorkspaceRepository', autospec=True)
async def test_get_airlock_requests_for_airlock_manager_no_roles(
    mock_workspace_repo,
    mock_access_service,
    mock_get_requests,
    airlock_request_repo
):
    # Mock no user roles
    mock_access_service.return_value.get_identity_role_assignments.return_value = []

    # Mock active workspaces
    mock_workspace_instance = MagicMock()
    mock_workspace_instance.get_active_workspaces = AsyncMock(return_value=[])
    mock_workspace_repo.create = AsyncMock(return_value=mock_workspace_instance)

    # Call function
    user = User(id="user1", name="TestUser")
    result = await airlock_request_repo.get_airlock_requests_for_airlock_manager(user)

    # validate
    assert result == []
    mock_get_requests.assert_not_called()


@pytest.mark.asyncio
@patch.object(AirlockRequestRepository, 'get_airlock_requests', new_callable=AsyncMock)
@patch('db.repositories.airlock_requests.get_access_service', autospec=True)
@patch('db.repositories.airlock_requests.WorkspaceRepository', autospec=True)
async def test_get_airlock_requests_for_airlock_manager_single_workspace(
    mock_workspace_repo,
    mock_access_service,
    mock_get_requests,
    airlock_request_repo
):
    # Setup workspace and manager role
    workspace = sample_workspace(workspace_properties={"app_role_id_workspace_airlock_manager": "manager-role-1"})
    mock_workspace_instance = MagicMock()
    mock_workspace_instance.get_active_workspaces = AsyncMock(return_value=[workspace])
    mock_workspace_repo.create = AsyncMock(return_value=mock_workspace_instance)

    # Setup user roles
    role_assignment = RoleAssignment(resource_id="resource_id", role_id="manager-role-1")
    mock_access_service.return_value.get_identity_role_assignments.return_value = [role_assignment]

    # Setup corresponding requests from that workspace
    request_mock = AirlockRequest(id="request-1", workspaceId=WORKSPACE_ID, type=AirlockRequestType.Import, reviews=[])
    mock_get_requests.return_value = [request_mock]

    user = User(id="user1", name="TestUser")
    result = await airlock_request_repo.get_airlock_requests_for_airlock_manager(user)

    assert len(result) == 1
    assert result[0].id == "request-1"
    mock_get_requests.assert_called_once_with(workspace_id=WORKSPACE_ID, type=None, status=None, order_by=None, order_ascending=True)


@pytest.mark.asyncio
@patch.object(AirlockRequestRepository, 'get_airlock_requests', new_callable=AsyncMock)
@patch('db.repositories.airlock_requests.get_access_service', autospec=True)
@patch('db.repositories.airlock_requests.WorkspaceRepository', autospec=True)
async def test_get_airlock_requests_for_airlock_manager_multiple_workspaces(
    mock_workspace_repo,
    mock_access_service,
    mock_get_requests,
    airlock_request_repo
):
    # Setup multiple workspaces
    workspace1 = sample_workspace(workspace_properties={"app_role_id_workspace_airlock_manager": "manager-role-1"})
    workspace2 = sample_workspace(workspace_properties={"app_role_id_workspace_airlock_manager": "manager-role-2"})
    mock_workspace_instance = MagicMock()
    mock_workspace_instance.get_active_workspaces = AsyncMock(return_value=[workspace1, workspace2])
    mock_workspace_repo.create = AsyncMock(return_value=mock_workspace_instance)

    # Setup user roles
    role_assignment_1 = RoleAssignment(resource_id="resource_id", role_id="manager-role-1")
    role_assignment_2 = RoleAssignment(resource_id="resource_id", role_id="manager-role-2")
    mock_access_service.return_value.get_identity_role_assignments.return_value = [role_assignment_1, role_assignment_2]

    # Setup requests for each workspace
    first_ws_requests = [AirlockRequest(id="request-1", workspaceId="workspace-1", type=AirlockRequestType.Import, reviews=[])]
    second_ws_requests = [AirlockRequest(id="request-2", workspaceId="workspace-2", type=AirlockRequestType.Import, reviews=[])]
    mock_get_requests.side_effect = [first_ws_requests, second_ws_requests]

    user = User(id="user1", name="TestUser")
    result = await airlock_request_repo.get_airlock_requests_for_airlock_manager(user)

    # combined requests from both
    assert len(result) == 2
    assert result[0].id == "request-1"
    assert result[1].id == "request-2"
    assert mock_get_requests.call_count == 2


@pytest.mark.asyncio
@patch.object(AirlockRequestRepository, 'get_airlock_requests', new_callable=AsyncMock)
@patch('db.repositories.airlock_requests.get_access_service', autospec=True)
@patch('db.repositories.airlock_requests.WorkspaceRepository', autospec=True)
async def test_get_airlock_requests_for_airlock_manager_active_workspaces_but_no_manager_role(
    mock_workspace_repo,
    mock_access_service,
    mock_get_requests,
    airlock_request_repo
):
    # Setup multiple workspaces, but user doesn't have manager roles
    workspace1 = sample_workspace(workspace_properties={"app_role_id_workspace_airlock_manager": "manager-role-1"})
    workspace2 = sample_workspace(workspace_properties={"app_role_id_workspace_airlock_manager": "manager-role-2"})
    mock_workspace_instance = MagicMock()
    mock_workspace_instance.get_active_workspaces = AsyncMock(return_value=[workspace1, workspace2])
    mock_workspace_repo.create = AsyncMock(return_value=mock_workspace_instance)

    # No matching roles for these workspaces
    mock_access_service.return_value.get_identity_role_assignments.return_value = [
        RoleAssignment(resource_id="resource_id", role_id="some-other-role")
    ]

    user = User(id="user1", name="TestUser")
    result = await airlock_request_repo.get_airlock_requests_for_airlock_manager(user)
    assert result == []
    mock_get_requests.assert_not_called()
