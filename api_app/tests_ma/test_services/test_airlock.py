from fastapi import HTTPException, status
import pytest
import pytest_asyncio
import time
from resources import strings
from services.airlock import validate_user_allowed_to_access_storage_account, get_required_permission, \
    validate_request_status, cancel_request, delete_review_user_resource, check_email_exists, revoke_request
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType, AirlockReview, AirlockReviewDecision, AirlockActions, AirlockReviewUserResource
from tests_ma.test_api.conftest import create_workspace_owner_user, create_workspace_researcher_user, get_required_roles
from mock import AsyncMock, patch, MagicMock
from models.domain.events import AirlockNotificationData, AirlockNotificationUserData, StatusChangedData, \
    AirlockNotificationRequestData, AirlockNotificationWorkspaceData, AirlockFile
from services.airlock import save_and_publish_event_airlock_request, \
    update_and_publish_event_airlock_request, get_airlock_requests_by_user_and_workspace, get_allowed_actions
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.workspace import Workspace
from tests_ma.test_api.conftest import create_test_user, create_workspace_airlock_manager_user
from azure.eventgrid import EventGridEvent
from api.routes.airlock import create_airlock_review, create_cancel_request, create_submit_request, create_revoke_request
from services.aad_authentication import AzureADAuthorization

WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "5dbc15ae-40e1-49a5-834b-595f59d626b7"
AIRLOCK_REVIEW_ID = "96d909c5-e913-4c05-ae53-668a702ba2e5"
USER_RESOURCE_ID = "cce59042-1dee-42dc-9388-6db846feeb3b"
WORKSPACE_SERVICE_ID = "30f2fefa-e7bb-4e5b-93aa-e50bb037502a"
CURRENT_TIME = time.time()
ALL_ROLES = AzureADAuthorization.WORKSPACE_ROLES_DICT.keys()


@pytest_asyncio.fixture
async def airlock_request_repo_mock(no_database):
    _ = no_database
    airlock_request_repo_mock = await AirlockRequestRepository().create()
    yield airlock_request_repo_mock


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


def sample_airlock_request(status=AirlockRequestStatus.Draft):
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        workspaceId=WORKSPACE_ID,
        type=AirlockRequestType.Import,
        reviewUserResources={"user-guid-here": sample_airlock_user_resource_object()},
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


def sample_airlock_user_resource_object():
    return AirlockReviewUserResource(
        workspaceId=WORKSPACE_ID,
        workspaceServiceId=WORKSPACE_SERVICE_ID,
        userResourceId=USER_RESOURCE_ID
    )


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
        decisionExplanation="test explanation"
    )
    return airlock_review


def test_validate_user_is_allowed_to_access_sa_blocks_access_as_expected():
    airlock_manager_user = create_workspace_airlock_manager_user()
    draft_airlock_request = sample_airlock_request()
    with pytest.raises(HTTPException) as ex:
        validate_user_allowed_to_access_storage_account(
            user=airlock_manager_user,
            airlock_request=draft_airlock_request
        )

    assert ex.value.status_code == status.HTTP_403_FORBIDDEN

    researcher_user = create_workspace_researcher_user()
    review_airlock_request = sample_airlock_request(AirlockRequestStatus.InReview)
    with pytest.raises(HTTPException) as ex:
        validate_user_allowed_to_access_storage_account(
            user=researcher_user,
            airlock_request=review_airlock_request
        )

    assert ex.value.status_code == status.HTTP_403_FORBIDDEN


def test_validate_user_is_allowed_to_access_grants_access_to_user_with_a_valid_role():
    ws_owner_user = create_workspace_owner_user()
    draft_airlock_request = sample_airlock_request(AirlockRequestStatus.InReview)

    assert (validate_user_allowed_to_access_storage_account(
        user=ws_owner_user,
        airlock_request=draft_airlock_request) is None)

    researcher_user = create_workspace_researcher_user()
    review_airlock_request = sample_airlock_request(AirlockRequestStatus.Approved)
    assert (
        validate_user_allowed_to_access_storage_account(
            user=researcher_user,
            airlock_request=review_airlock_request
        ) is None)


@pytest.mark.parametrize('airlock_status',
                         [AirlockRequestStatus.ApprovalInProgress,
                          AirlockRequestStatus.RejectionInProgress,
                          AirlockRequestStatus.BlockingInProgress])
def test_validate_request_status_raises_error_for_in_progress_request(airlock_status):
    airlock_request = sample_airlock_request(airlock_status)
    with pytest.raises(HTTPException) as ex:
        validate_request_status(airlock_request)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST
    assert ex.value.detail == strings.AIRLOCK_REQUEST_IN_PROGRESS


def test_validate_request_status_raises_error_for_canceled_request():
    airlock_request = sample_airlock_request(AirlockRequestStatus.Cancelled)
    with pytest.raises(HTTPException) as ex:
        validate_request_status(airlock_request)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST
    assert ex.value.detail == strings.AIRLOCK_REQUEST_IS_CANCELED


@pytest.mark.parametrize('airlock_status',
                         [AirlockRequestStatus.Failed,
                          AirlockRequestStatus.Rejected,
                          AirlockRequestStatus.Blocked])
def test_validate_request_status_raises_error_for_unaccessible_request(airlock_status):
    airlock_request = sample_airlock_request(airlock_status)
    with pytest.raises(HTTPException) as ex:
        validate_request_status(airlock_request)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST
    assert ex.value.detail == strings.AIRLOCK_REQUEST_UNACCESSIBLE


@pytest.mark.parametrize('airlock_status',
                         [AirlockRequestStatus.Submitted,
                          AirlockRequestStatus.InReview,
                          AirlockRequestStatus.ApprovalInProgress,
                          AirlockRequestStatus.Approved,
                          AirlockRequestStatus.RejectionInProgress,
                          AirlockRequestStatus.Rejected,
                          AirlockRequestStatus.Cancelled,
                          AirlockRequestStatus.BlockingInProgress,
                          AirlockRequestStatus.Blocked])
def test_get_required_permission_return_read_only_permissions_for_non_draft_requests(airlock_status):
    airlock_request = sample_airlock_request(airlock_status)
    permissions = get_required_permission(airlock_request)
    assert permissions.write is False
    assert permissions.delete is False
    assert permissions.read is True
    assert permissions.list is True


def test_get_required_permission_return_read_and_write_permissions_for_draft_requests():
    airlock_request = sample_airlock_request(AirlockRequestStatus.Draft)
    permissions = get_required_permission(airlock_request)
    assert permissions.write is True
    assert permissions.delete is True
    assert permissions.list is True
    assert permissions.read is True


@pytest.mark.asyncio
@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
@patch('services.airlock.get_timestamp', return_value=CURRENT_TIME)
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


@pytest.mark.asyncio
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
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


@pytest.mark.asyncio
@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
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


@pytest.mark.asyncio
@pytest.mark.parametrize('role_assignment_details_mock_return', [{},
                         {"AirlockManager": ["owner@outlook.com"]},
                         {"WorkspaceResearcher": [], "AirlockManager": ["owner@outlook.com"]},
                         {"WorkspaceResearcher": ["researcher@outlook.com"], "owner_emails": []},
                         {"WorkspaceResearcher": ["researcher@outlook.com"]}])
async def test_check_email_exists_raises_417_if_email_not_present(role_assignment_details_mock_return):
    role_assignment_details = role_assignment_details_mock_return
    with pytest.raises(HTTPException) as ex:
        check_email_exists(role_assignment_details)
    assert ex.value.status_code == status.HTTP_417_EXPECTATION_FAILED


@pytest.mark.asyncio
@pytest.mark.parametrize('role_assignment_details_mock_return', [
                         {"AirlockManager": ["manager@outlook.com"], "WorkspaceResearcher": ["researcher@outlook.com"], },
                         {"AirlockManager": ["manager@outlook.com"], "WorkspaceOwner": ["researcher@outlook.com"], },
                         {"AirlockManager": ["manager@outlook.com"], "WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"]}])
async def test_check_email_exists_passes_if_researcher_or_owner_and_airlock_manager_email_present(role_assignment_details_mock_return):
    role_assignment_details = role_assignment_details_mock_return
    result = check_email_exists(role_assignment_details)
    assert result is None


@pytest.mark.asyncio
@pytest.mark.parametrize('email_mock_return', [{},
                                               {"AirlockManager": ["owner@outlook.com"]},
                                               {"WorkspaceResearcher": [], "AirlockManager": ["owner@outlook.com"]},
                                               {"WorkspaceResearcher": ["researcher@outlook.com"], "owner_emails": []},
                                               {"WorkspaceResearcher": ["researcher@outlook.com"]}])
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment")
@patch('core.config.ENABLE_AIRLOCK_EMAIL_CHECK', "True")
async def test_save_and_publish_event_airlock_request_raises_417_if_email_not_present(get_workspace_user_emails_by_role_assignment_patched, email_mock_return):

    get_workspace_user_emails_by_role_assignment_patched.return_value = email_mock_return
    airlock_request_mock = sample_airlock_request()

    with pytest.raises(HTTPException) as ex:
        await save_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=None,
            user=create_test_user(),
            workspace=sample_workspace())
    assert ex.value.status_code == status.HTTP_417_EXPECTATION_FAILED


@pytest.mark.asyncio
@pytest.mark.parametrize('email_mock_return', [{},
                                               {"WorkspaceResearcher": [], "AirlockManager": []}])
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment")
@patch("event_grid.event_sender.publish_event", return_value=AsyncMock())
async def test_save_and_publish_event_airlock_notification_if_email_not_present(publish_event_mock, get_workspace_user_emails_by_role_assignment_patched, email_mock_return, airlock_request_repo_mock):

    get_workspace_user_emails_by_role_assignment_patched.return_value = email_mock_return
    airlock_request_mock = sample_airlock_request()
    airlock_request_repo_mock.save_item = AsyncMock()

    await save_and_publish_event_airlock_request(
        airlock_request=airlock_request_mock,
        airlock_request_repo=airlock_request_repo_mock,
        user=create_test_user(),
        workspace=sample_workspace())

    assert publish_event_mock.call_count == 2


@pytest.mark.asyncio
@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
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


@pytest.mark.asyncio
@patch("services.airlock.send_status_changed_event")
@patch("services.airlock.send_airlock_notification_event")
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment")
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


@pytest.mark.asyncio
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
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


@pytest.mark.asyncio
@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]})
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


@pytest.mark.asyncio
@patch("services.airlock.send_status_changed_event")
@patch("services.airlock.send_airlock_notification_event")
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment")
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


@pytest.mark.asyncio
async def test_get_airlock_requests_by_user_and_workspace_with_status_filter_calls_repo(airlock_request_repo_mock):
    workspace = sample_workspace()
    user = create_workspace_airlock_manager_user()
    airlock_request_repo_mock.get_airlock_requests = AsyncMock()

    await get_airlock_requests_by_user_and_workspace(user=user, workspace=workspace, airlock_request_repo=airlock_request_repo_mock,
                                                     status=AirlockRequestStatus.InReview)

    airlock_request_repo_mock.get_airlock_requests.assert_called_once_with(workspace_id=workspace.id, creator_user_id=None, type=None,
                                                                           status=AirlockRequestStatus.InReview, order_by=None, order_ascending=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("action, required_roles, airlock_request_repo_mock", [
    (AirlockActions.Review, get_required_roles(endpoint=create_airlock_review), airlock_request_repo_mock),
    (AirlockActions.Cancel, get_required_roles(endpoint=create_cancel_request), airlock_request_repo_mock),
    (AirlockActions.Submit, get_required_roles(endpoint=create_submit_request), airlock_request_repo_mock),
    (AirlockActions.Revoke, get_required_roles(endpoint=create_revoke_request), airlock_request_repo_mock)])
async def test_get_allowed_actions_requires_same_roles_as_endpoint(action, required_roles, airlock_request_repo_mock):
    airlock_request_repo_mock.validate_status_update = MagicMock(return_value=True)
    user = create_test_user()
    for role in required_roles:
        user.roles = [role]
        allowed_actions = get_allowed_actions(request=sample_airlock_request(), user=user, airlock_request_repo=airlock_request_repo_mock)
        assert action in allowed_actions


@pytest.mark.asyncio
@pytest.mark.parametrize("action, endpoint_roles, airlock_request_repo_mock", [
    (AirlockActions.Review, get_required_roles(endpoint=create_airlock_review), airlock_request_repo_mock),
    (AirlockActions.Cancel, get_required_roles(endpoint=create_cancel_request), airlock_request_repo_mock),
    (AirlockActions.Submit, get_required_roles(endpoint=create_submit_request), airlock_request_repo_mock),
    (AirlockActions.Revoke, get_required_roles(endpoint=create_revoke_request), airlock_request_repo_mock)])
async def test_get_allowed_actions_does_not_return_actions_that_are_forbidden_to_the_user_role(action, endpoint_roles, airlock_request_repo_mock):
    airlock_request_repo_mock.validate_status_update = MagicMock(return_value=True)
    user = create_test_user()
    forbidden_roles = [role for role in ALL_ROLES if role not in endpoint_roles]
    for forbidden_role in forbidden_roles:
        user.roles = [forbidden_role]
        allowed_actions = get_allowed_actions(request=sample_airlock_request(), user=user, airlock_request_repo=airlock_request_repo_mock)
        assert action not in allowed_actions


@pytest.mark.asyncio
@patch("services.airlock.update_and_publish_event_airlock_request")
async def test_revoke_request_calls_update_with_revoked_status(update_mock, airlock_request_repo_mock):
    user = create_test_user()
    workspace = sample_workspace()
    airlock_request = sample_airlock_request(status=AirlockRequestStatus.Approved)
    revocation_reason = "Test revocation reason"

    update_mock.return_value = sample_airlock_request(status=AirlockRequestStatus.Revoked)
    airlock_request_repo_mock.create_airlock_revoke_review_item = MagicMock(return_value=sample_airlock_review())

    result = await revoke_request(
        airlock_request=airlock_request,
        user=user,
        workspace=workspace,
        airlock_request_repo=airlock_request_repo_mock,
        revocation_reason=revocation_reason
    )

    # Verify that a revoke review is created
    airlock_request_repo_mock.create_airlock_revoke_review_item.assert_called_once_with(revocation_reason, user)

    # Verify update is called with review and status
    update_mock.assert_called_once()
    args, kwargs = update_mock.call_args
    assert kwargs['airlock_request'] == airlock_request
    assert kwargs['airlock_request_repo'] == airlock_request_repo_mock
    assert kwargs['updated_by'] == user
    assert kwargs['workspace'] == workspace
    assert kwargs['new_status'] == AirlockRequestStatus.Revoked
    assert kwargs['airlock_review'] is not None

    assert result.status == AirlockRequestStatus.Revoked


@pytest.mark.asyncio
@patch("services.airlock.delete_review_user_resource")
@patch("services.airlock.update_and_publish_event_airlock_request")
async def test_cancel_request_deletes_review_resource(_, delete_review_user_resource, airlock_request_repo_mock):
    await cancel_request(
        airlock_request=sample_airlock_request(),
        user=create_test_user(),
        airlock_request_repo=airlock_request_repo_mock,
        workspace=sample_workspace(),
        user_resource_repo=AsyncMock(),
        workspace_service_repo=AsyncMock(),
        resource_template_repo=AsyncMock(),
        operations_repo=AsyncMock(),
        resource_history_repo=AsyncMock())

    delete_review_user_resource.assert_called_once()


@pytest.mark.asyncio
@patch("services.airlock.disable_user_resource")
@patch("services.airlock.send_uninstall_message")
@patch("services.airlock.update_and_publish_event_airlock_request")
async def test_delete_review_user_resource_disables_the_resource_before_deletion(_, __, disable_user_resource):
    await delete_review_user_resource(user_resource=AsyncMock(),
                                      user_resource_repo=AsyncMock(),
                                      workspace_service_repo=AsyncMock(),
                                      resource_template_repo=AsyncMock(),
                                      operations_repo=AsyncMock(),
                                      resource_history_repo=AsyncMock(),
                                      user=create_test_user())
    disable_user_resource.assert_called_once()
