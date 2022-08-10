from fastapi import HTTPException, status
import pytest
from mock import AsyncMock, patch, MagicMock

from models.domain.events import AirlockNotificationData, StatusChangedData
from api.routes.airlock_resource_helpers import save_and_publish_event_airlock_request, \
    update_status_and_publish_event_airlock_request
from db.repositories.airlock_requests import AirlockRequestRepository
from models.domain.workspace import Workspace
from tests_ma.test_api.conftest import create_test_user
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType, AirlockReview, AirlockReviewDecision
from azure.eventgrid import EventGridEvent

pytestmark = pytest.mark.asyncio

WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "5dbc15ae-40e1-49a5-834b-595f59d626b7"
AIRLOCK_REVIEW_ID = "96d909c5-e913-4c05-ae53-668a702ba2e5"


def sample_workspace():
    return Workspace(id=WORKSPACE_ID, templateName='template name', templateVersion='1.0', etag='', properties={"client_id": "12345"}, resourcePath="test")


@pytest.fixture
def airlock_request_repo_mock():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield AirlockRequestRepository(cosmos_client_mock)


def sample_airlock_request(status=AirlockRequestStatus.Draft):
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        workspaceId=WORKSPACE_ID,
        requestType=AirlockRequestType.Import,
        files=[],
        businessJustification="some test reason",
        status=status
    )
    return airlock_request


def sample_status_changed_event(status="draft"):
    status_changed_event = EventGridEvent(
        event_type="statusChanged",
        data=StatusChangedData(request_id=AIRLOCK_REQUEST_ID, status=status, type=AirlockRequestType.Import, workspace_id=WORKSPACE_ID[-4:]).__dict__,
        subject=f"{AIRLOCK_REQUEST_ID}/statusChanged",
        data_version="2.0"
    )
    return status_changed_event


def sample_airlock_notification_event(status="draft"):
    status_changed_event = EventGridEvent(
        event_type="airlockNotification",
        data=AirlockNotificationData(request_id=AIRLOCK_REQUEST_ID, event_type="status_changed", event_value=status, researchers_emails=['researcher@outlook.com'], owners_emails=['owner@outlook.com'], workspace_id=WORKSPACE_ID[-4:]).__dict__,
        subject=f"{AIRLOCK_REQUEST_ID}/airlockNotification",
        data_version="2.0"
    )
    return status_changed_event


def sample_airlock_review(review_decision=AirlockReviewDecision.Approved):
    airlock_review = AirlockReview(
        id=AIRLOCK_REVIEW_ID,
        reviewDecision=review_decision,
        decisionExplanation="test explaination"
    )
    return airlock_review


@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]})
async def test_save_and_publish_event_airlock_request_saves_item(_, event_grid_publisher_client_mock,
                                                                 airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    airlock_request_repo_mock.save_item = MagicMock(return_value=None)
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


@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]})
async def test_save_and_publish_event_airlock_request_raises_503_if_save_to_db_fails(_, airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    airlock_request_repo_mock.save_item = MagicMock(side_effect=Exception)

    with pytest.raises(HTTPException) as ex:
        await save_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            user=create_test_user(),
            workspace=sample_workspace())
    assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]})
async def test_save_and_publish_event_airlock_request_raises_503_if_publish_event_fails(_, event_grid_publisher_client_mock,
                                                                                        airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    airlock_request_repo_mock.save_item = MagicMock(return_value=None)
    # When eventgrid fails, it deletes the saved request
    airlock_request_repo_mock.delete_item = MagicMock(return_value=None)
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
                                               {"owner_emails": ["owner@outlook.com"]},
                                               {"researcher_emails": [], "owner_emails": ["owner@outlook.com"]},
                                               {"researcher_emails": ["researcher@outlook.com"], "owner_emails": []},
                                               {"researcher_emails": ["researcher@outlook.com"]}])
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
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]})
async def test_update_status_and_publish_event_airlock_request_updates_item(_, event_grid_publisher_client_mock,
                                                                            airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    updated_airlock_request_mock = sample_airlock_request(status=AirlockRequestStatus.Submitted)
    status_changed_event_mock = sample_status_changed_event(status="submitted")
    airlock_notification_event_mock = sample_airlock_notification_event(status="submitted")
    airlock_request_repo_mock.update_airlock_request_status = MagicMock(return_value=updated_airlock_request_mock)
    event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
    event_grid_sender_client_mock.send = AsyncMock()

    actual_updated_airlock_request = await update_status_and_publish_event_airlock_request(
        airlock_request=airlock_request_mock,
        airlock_request_repo=airlock_request_repo_mock,
        user=create_test_user(),
        new_status=AirlockRequestStatus.Submitted,
        workspace=sample_workspace())

    airlock_request_repo_mock.update_airlock_request_status.assert_called_once()
    assert (actual_updated_airlock_request == updated_airlock_request_mock)

    assert event_grid_sender_client_mock.send.call_count == 2
    # Since the eventgrid object has the update time attribute which differs, we only compare the data that was sent
    actual_status_changed_event = event_grid_sender_client_mock.send.await_args_list[0].args[0][0]
    assert actual_status_changed_event.data == status_changed_event_mock.data
    actual_airlock_notification_event = event_grid_sender_client_mock.send.await_args_list[1].args[0][0]
    assert actual_airlock_notification_event.data == airlock_notification_event_mock.data


@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]})
async def test_update_status_and_publish_event_airlock_request_raises_400_if_status_update_invalid(_, airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()

    with pytest.raises(HTTPException) as ex:
        await update_status_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            user=create_test_user(),
            new_status=AirlockRequestStatus.Approved,
            workspace=sample_workspace())

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST


@patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
@patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]})
async def test_update_status_and_publish_event_airlock_request_raises_503_if_publish_event_fails(_, event_grid_publisher_client_mock,
                                                                                                 airlock_request_repo_mock):
    airlock_request_mock = sample_airlock_request()
    updated_airlock_request_mock = sample_airlock_request(status=AirlockRequestStatus.Submitted)
    airlock_request_repo_mock.update_airlock_request_status = MagicMock(return_value=updated_airlock_request_mock)
    event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
    event_grid_sender_client_mock.send = AsyncMock(side_effect=Exception)

    with pytest.raises(HTTPException) as ex:
        await update_status_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            user=create_test_user(),
            new_status=AirlockRequestStatus.Submitted,
            workspace=sample_workspace())
    assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE



