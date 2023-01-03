import time
from fastapi import HTTPException, status
import pytest
import pytest_asyncio
from mock import AsyncMock, patch, MagicMock

from models.domain.events import AirlockNotificationData, AirlockNotificationUserData, StatusChangedData, \
    AirlockNotificationRequestData, AirlockNotificationWorkspaceData, AirlockRequestStatus, AirlockFile, AirlockRequestType
from api.routes.airlock_resource_helpers import save_and_publish_event_airlock_request, \
    update_and_publish_event_airlock_request, get_airlock_requests_by_user_and_workspace, get_allowed_actions
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.workspace import Workspace
from tests_ma.test_api.conftest import create_test_user, create_workspace_airlock_manager_user
from models.domain.airlock_request import AirlockRequest, AirlockReview, AirlockReviewDecision, AirlockActions
from azure.eventgrid import EventGridEvent
from api.routes.airlock import create_airlock_review, create_cancel_request, create_submit_request

pytestmark = pytest.mark.asyncio

WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "5dbc15ae-40e1-49a5-834b-595f59d626b7"
AIRLOCK_REVIEW_ID = "96d909c5-e913-4c05-ae53-668a702ba2e5"
CURRENT_TIME = time.time()


def sample_workspace():
    return Workspace(
        id=WORKSPACE_ID,
        templateName='template name',
        templateVersion='1.0',
        etag='',
        properties={
            "client_id": "12345",
            "display_name": "my research workspace",
            "description": "for science!"},
        resourcePath="test")


@pytest_asyncio.fixture
async def airlock_request_repo_mock():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        airlock_request_repo_mock = await AirlockRequestRepository.create(cosmos_client_mock)
        yield airlock_request_repo_mock


def sample_airlock_request(status=AirlockRequestStatus.Draft):
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        workspaceId=WORKSPACE_ID,
        type=AirlockRequestType.Import,
        files=[AirlockFile(
            name="data.txt",
            size=5
        )],
        businessJustification="some test reason",
        status=status,
        createdWhen=CURRENT_TIME,
        createdBy=AirlockNotificationUserData(
            name="John Doe",
            email="john@example.com"
        ),
        updatedWhen=CURRENT_TIME,
        updatedBy=AirlockNotificationUserData(
            name="Test User",
            email="test@user.com"
        )
    )
    return airlock_request


def sample_status_changed_event(new_status="draft", previous_status=None):
    status_changed_event = EventGridEvent(
        event_type="statusChanged",
        data=StatusChangedData(request_id=AIRLOCK_REQUEST_ID, new_status=new_status, previous_status=previous_status, type=AirlockRequestType.Import, workspace_id=WORKSPACE_ID[-4:]).__dict__,
        subject=f"{AIRLOCK_REQUEST_ID}/statusChanged",
        data_version="2.0"
    )
    return status_changed_event


def sample_airlock_notification_event(status="draft"):
    status_changed_event = EventGridEvent(
        event_type="airlockNotification",
        data=AirlockNotificationData(
            event_type="status_changed",
            recipient_emails_by_role={"workspace_researcher": ["researcher@outlook.com"], "workspace_owner": ["owner@outlook.com"], "airlock_manager": ["manager@outlook.com"]},
            request=AirlockNotificationRequestData(
                id=AIRLOCK_REQUEST_ID,
                created_when=CURRENT_TIME,
                created_by=AirlockNotificationUserData(
                    name="John Doe",
                    email="john@example.com"
                ),
                updated_when=CURRENT_TIME,
                updated_by=AirlockNotificationUserData(
                    name="Test User",
                    email="test@user.com"
                ),
                request_type=AirlockRequestType.Import,
                files=[AirlockFile(
                    name="data.txt",
                    size=5
                )],
                status=status,
                business_justification="some test reason"
            ),
            workspace=AirlockNotificationWorkspaceData(
                id=WORKSPACE_ID,
                display_name="my research workspace",
                description="for science!"
            )),
        subject=f"{AIRLOCK_REQUEST_ID}/airlockNotification",
        data_version="4.0"
    )
    return status_changed_event


def sample_airlock_review(review_decision=AirlockReviewDecision.Approved):
    airlock_review = AirlockReview(
        id=AIRLOCK_REVIEW_ID,
        reviewDecision=review_decision,
        decisionExplanation="test explaination"
    )
    return airlock_review


def get_required_roles(endpoint):
    dependencies = list(filter(lambda x: hasattr(x.dependency, 'require_one_of_roles'), endpoint.__defaults__))
    required_roles = dependencies[0].dependency.require_one_of_roles
    return required_roles


@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
@patch('api.routes.airlock_resource_helpers.get_timestamp', return_value=CURRENT_TIME)
async def test_save_and_publish_event_airlock_request_saves_item(_, __, event_grid_publisher_client_mock, airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    airlock_request_repo_mock.save_item = AsyncMock(return_value=None)
    status_changed_event_mock = sample_status_changed_event()
    airlock_notification_event_mock = sample_airlock_notification_event()
    event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
    event_grid_sender_client_mock.send = AsyncMock()

    await save_and_publish_event_airlock_request(
        airlock_request=airlock_request_mock,
        airlock_request_repo=airlock_request_repo_mock,
        user=create_test_user(),
        workspace=sample_workspace())

    airlock_request_repo_mock.save_item.assert_called_once_with(airlock_request_mock)

    assert event_grid_sender_client_mock.send.call_count == 2
    # Since the eventgrid object has the update time attribute which differs, we only compare the data that was sent
    actual_status_changed_event = event_grid_sender_client_mock.send.await_args_list[0].args[0][0]
    assert actual_status_changed_event.data == status_changed_event_mock.data
    actual_airlock_notification_event = event_grid_sender_client_mock.send.await_args_list[1].args[0][0]
    assert actual_airlock_notification_event.data == airlock_notification_event_mock.data


@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
async def test_save_and_publish_event_airlock_request_raises_503_if_save_to_db_fails(_, airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    airlock_request_repo_mock.save_item = AsyncMock(side_effect=Exception)

    with pytest.raises(HTTPException) as ex:
        await save_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            user=create_test_user(),
            workspace=sample_workspace())
    assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
async def test_save_and_publish_event_airlock_request_raises_503_if_publish_event_fails(_, event_grid_publisher_client_mock,
                                                                                        airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    airlock_request_repo_mock.save_item = AsyncMock(return_value=None)
    # When eventgrid fails, it deletes the saved request
    airlock_request_repo_mock.delete_item = AsyncMock(return_value=None)
    event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
    event_grid_sender_client_mock.send = AsyncMock(side_effect=Exception)

    with pytest.raises(HTTPException) as ex:
        await save_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            user=create_test_user(),
            workspace=sample_workspace())
    assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.parametrize('email_mock_return', [{},
                                               {"AirlockManager": ["owner@outlook.com"]},
                                               {"WorkspaceResearcher": [], "AirlockManager": ["owner@outlook.com"]},
                                               {"WorkspaceResearcher": ["researcher@outlook.com"], "owner_emails": []},
                                               {"WorkspaceResearcher": ["researcher@outlook.com"]}])
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details")
async def test_save_and_publish_event_airlock_request_raises_417_if_email_not_present(get_workspace_role_assignment_details_patched, email_mock_return):

    get_workspace_role_assignment_details_patched.return_value = email_mock_return
    airlock_request_mock = sample_airlock_request()

    with pytest.raises(HTTPException) as ex:
        await save_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=None,
            user=create_test_user(),
            workspace=sample_workspace())
    assert ex.value.status_code == status.HTTP_417_EXPECTATION_FAILED


@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
async def test_update_and_publish_event_airlock_request_updates_item(_, event_grid_publisher_client_mock,
                                                                     airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    updated_airlock_request_mock = sample_airlock_request(status=AirlockRequestStatus.Submitted)
    status_changed_event_mock = sample_status_changed_event(new_status="submitted", previous_status="draft")
    airlock_notification_event_mock = sample_airlock_notification_event(status="submitted")
    airlock_request_repo_mock.update_airlock_request = AsyncMock(return_value=updated_airlock_request_mock)
    event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
    event_grid_sender_client_mock.send = AsyncMock()

    actual_updated_airlock_request = await update_and_publish_event_airlock_request(
        airlock_request=airlock_request_mock,
        airlock_request_repo=airlock_request_repo_mock,
        updated_by=create_test_user(),
        new_status=AirlockRequestStatus.Submitted,
        workspace=sample_workspace())

    airlock_request_repo_mock.update_airlock_request.assert_called_once()
    assert (actual_updated_airlock_request == updated_airlock_request_mock)

    assert event_grid_sender_client_mock.send.call_count == 2
    # Since the eventgrid object has the update time attribute which differs, we only compare the data that was sent
    actual_status_changed_event = event_grid_sender_client_mock.send.await_args_list[0].args[0][0]
    assert actual_status_changed_event.data == status_changed_event_mock.data
    actual_airlock_notification_event = event_grid_sender_client_mock.send.await_args_list[1].args[0][0]
    assert actual_airlock_notification_event.data == airlock_notification_event_mock.data


@patch("api.routes.airlock_resource_helpers.send_status_changed_event")
@patch("api.routes.airlock_resource_helpers.send_airlock_notification_event")
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details")
async def test_update_and_publish_event_airlock_request_sends_status_changed_event(_, send_airlock_notification_event_mock, send_status_changed_event_mock, airlock_request_repo_mock):
    new_status = AirlockRequestStatus.Submitted
    airlock_request_repo_mock.update_airlock_request = AsyncMock()

    await update_and_publish_event_airlock_request(
        airlock_request=sample_airlock_request(),
        airlock_request_repo=airlock_request_repo_mock,
        updated_by=create_test_user(),
        new_status=new_status,
        workspace=sample_workspace())

    assert send_status_changed_event_mock.call_count == 1
    assert send_airlock_notification_event_mock.call_count == 1


@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
async def test_update_and_publish_event_airlock_request_raises_400_if_status_update_invalid(_, airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()

    with pytest.raises(HTTPException) as ex:
        await update_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            updated_by=create_test_user(),
            new_status=AirlockRequestStatus.Approved,
            workspace=sample_workspace())

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST


@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
async def test_update_and_publish_event_airlock_request_raises_503_if_publish_event_fails(_, event_grid_publisher_client_mock,
                                                                                          airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    updated_airlock_request_mock = sample_airlock_request(status=AirlockRequestStatus.Submitted)
    airlock_request_repo_mock.update_airlock_request = AsyncMock(return_value=updated_airlock_request_mock)
    event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
    event_grid_sender_client_mock.send = AsyncMock(side_effect=Exception)

    with pytest.raises(HTTPException) as ex:
        await update_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            updated_by=create_test_user(),
            new_status=AirlockRequestStatus.Submitted,
            workspace=sample_workspace())
    assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@patch("api.routes.airlock_resource_helpers.send_status_changed_event")
@patch("api.routes.airlock_resource_helpers.send_airlock_notification_event")
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details")
async def test_update_and_publish_event_airlock_request_without_status_change_should_not_send_status_changed_event(_, send_airlock_notification_event_mock, send_status_changed_event_mock, airlock_request_repo_mock):
    new_status = None
    airlock_request_repo_mock.update_airlock_request = AsyncMock()

    await update_and_publish_event_airlock_request(
        airlock_request=sample_airlock_request(),
        airlock_request_repo=airlock_request_repo_mock,
        updated_by=create_test_user(),
        new_status=new_status,
        workspace=sample_workspace())

    assert send_status_changed_event_mock.call_count == 0
    assert send_airlock_notification_event_mock.call_count == 0


async def test_get_airlock_requests_by_user_and_workspace_with_status_filter_calls_repo(airlock_request_repo_mock):
    workspace = sample_workspace()
    user = create_workspace_airlock_manager_user()
    airlock_request_repo_mock.get_airlock_requests = AsyncMock()

    await get_airlock_requests_by_user_and_workspace(user=user, workspace=workspace, airlock_request_repo=airlock_request_repo_mock,
                                                     status=AirlockRequestStatus.InReview)

    airlock_request_repo_mock.get_airlock_requests.assert_called_once_with(workspace_id=workspace.id, creator_user_id=None, type=None,
                                                                           status=AirlockRequestStatus.InReview, order_by=None, order_ascending=True)


@pytest.mark.parametrize("action, required_roles, airlock_request_repo_mock", [
    (AirlockActions.Review, get_required_roles(endpoint=create_airlock_review), airlock_request_repo_mock),
    (AirlockActions.Cancel, get_required_roles(endpoint=create_cancel_request), airlock_request_repo_mock),
    (AirlockActions.Submit, get_required_roles(endpoint=create_submit_request), airlock_request_repo_mock)])
async def test_get_allowed_actions_requires_same_roles_as_endpoint(action, required_roles, airlock_request_repo_mock):
    airlock_request_repo_mock.validate_status_update = MagicMock(return_value=True)
    user = create_test_user()
    for role in required_roles:
        user.roles = [role]
        allowed_actions = get_allowed_actions(request=sample_airlock_request(), user=user, airlock_request_repo=airlock_request_repo_mock)
        assert action in allowed_actions
