from fastapi import HTTPException, status
import pytest
from mock import AsyncMock, patch, MagicMock

from api.routes.airlock_resource_helpers import save_airlock_review, save_and_publish_event_airlock_request, update_status_and_publish_event_airlock_request
from db.repositories.airlock_reviews import AirlockReviewRepository
from db.repositories.airlock_requests import AirlockRequestRepository
from tests_ma.test_api.conftest import create_test_user
from models.domain.airlock_review import AirlockReview, AirlockReviewDecision
from models.domain.airlock_resource import AirlockResourceType
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockRequestType
from azure.eventgrid import EventGridEvent

pytestmark = pytest.mark.asyncio


WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "5dbc15ae-40e1-49a5-834b-595f59d626b7"
AIRLOCK_REVIEW_ID = "96d909c5-e913-4c05-ae53-668a702ba2e5"


@pytest.fixture
def airlock_request_repo_mock():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield AirlockRequestRepository(cosmos_client_mock)


@pytest.fixture
def airlock_review_repo_mock():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield AirlockReviewRepository(cosmos_client_mock)


def sample_airlock_request():
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        resourceType=AirlockResourceType.AirlockRequest,
        workspaceId=WORKSPACE_ID,
        requestType=AirlockRequestType.Import,
        files=[],
        businessJustification="some test reason"
    )
    return airlock_request


def sample_airlock_request_updated():
    airlock_request = AirlockRequest(
        id=AIRLOCK_REQUEST_ID,
        resourceType=AirlockResourceType.AirlockRequest,
        workspaceId=WORKSPACE_ID,
        requestType=AirlockRequestType.Import,
        files=[],
        businessJustification="some test reason",
        status=AirlockRequestStatus.Submitted
    )
    return airlock_request


def sample_status_changed_event_after_update():
    status_changed_event = EventGridEvent(
        event_type="statusChanged",
        data={
            "request_id": AIRLOCK_REQUEST_ID,
            "status": "submitted",
            "type": AirlockRequestType.Import,
            "workspace_id": WORKSPACE_ID[-4:]
        },
        subject=f"{AIRLOCK_REQUEST_ID}/statusChanged",
        data_version="2.0"
    )
    return status_changed_event


def sample_status_changed_event():
    status_changed_event = EventGridEvent(
        event_type="statusChanged",
        data={
            "request_id": AIRLOCK_REQUEST_ID,
            "status": "draft",
            "type": AirlockRequestType.Import,
            "workspace_id": WORKSPACE_ID[-4:]
        },
        subject=f"{AIRLOCK_REQUEST_ID}/statusChanged",
        data_version="2.0"
    )
    return status_changed_event


def sample_airlock_review():
    airlock_review = AirlockReview(
        id=AIRLOCK_REVIEW_ID,
        resourceType=AirlockResourceType.AirlockReview,
        workspaceId=WORKSPACE_ID,
        requestId=AIRLOCK_REQUEST_ID,
        reviewDecision=AirlockReviewDecision.Approved,
        decisionExplanation="test explaination"
    )
    return airlock_review


class TestAirlockResourceHelpers:
    @patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
    async def test_save_and_publish_event_airlock_request_saves_item(self, event_grid_publisher_client_mock, airlock_request_repo_mock):
        airlock_request_mock = sample_airlock_request()
        airlock_request_repo_mock.save_item = MagicMock(return_value=None)
        status_changed_event_mock = sample_status_changed_event()
        event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
        event_grid_sender_client_mock.send = AsyncMock()

        await save_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            user=create_test_user())

        airlock_request_repo_mock.save_item.assert_called_once_with(airlock_request_mock)

        event_grid_sender_client_mock.send.assert_awaited_once()
        # Since the eventgrid object has the update time attribute which differs, we only compare the data that was sent
        actual_status_changed_event = event_grid_sender_client_mock.send.await_args[0][0][0]
        assert(actual_status_changed_event.data == status_changed_event_mock.data)

    async def test_save_and_publish_event_airlock_request_raises_503_if_save_to_db_fails(self, airlock_request_repo_mock):
        airlock_request_mock = sample_airlock_request()
        airlock_request_repo_mock.save_item = MagicMock(side_effect=Exception)

        with pytest.raises(HTTPException) as ex:
            await save_and_publish_event_airlock_request(
                airlock_request=airlock_request_mock,
                airlock_request_repo=airlock_request_repo_mock,
                user=create_test_user())
        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
    async def test_save_and_publish_event_airlock_request_raises_503_if_publish_event_fails(self, event_grid_publisher_client_mock, airlock_request_repo_mock):
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
                user=create_test_user())
        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
    async def test_update_status_and_publish_event_airlock_request_updates_item(self, event_grid_publisher_client_mock, airlock_request_repo_mock):
        airlock_request_mock = sample_airlock_request()
        updated_airlock_request_mock = sample_airlock_request_updated()
        status_changed_event_mock = sample_status_changed_event_after_update()
        airlock_request_repo_mock.update_airlock_request_status = MagicMock(return_value=updated_airlock_request_mock)
        event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
        event_grid_sender_client_mock.send = AsyncMock()

        actual_updated_airlock_request = await update_status_and_publish_event_airlock_request(
            airlock_request=airlock_request_mock,
            airlock_request_repo=airlock_request_repo_mock,
            user=create_test_user(),
            new_status=AirlockRequestStatus.Submitted)

        airlock_request_repo_mock.update_airlock_request_status.assert_called_once()
        assert(actual_updated_airlock_request == updated_airlock_request_mock)

        event_grid_sender_client_mock.send.assert_awaited_once()
        # Since the eventgrid object has the update time attribute which differs, we only compare the data that was sent
        actual_status_changed_event = event_grid_sender_client_mock.send.await_args[0][0][0]
        assert(actual_status_changed_event.data == status_changed_event_mock.data)

    async def test_update_status_and_publish_event_airlock_request_raises_400_if_status_update_invalid(self, airlock_request_repo_mock):
        airlock_request_mock = sample_airlock_request()

        with pytest.raises(HTTPException) as ex:
            await update_status_and_publish_event_airlock_request(
                airlock_request=airlock_request_mock,
                airlock_request_repo=airlock_request_repo_mock,
                user=create_test_user(),
                new_status=AirlockRequestStatus.Approved)

        assert ex.value.status_code == status.HTTP_400_BAD_REQUEST

    @patch("event_grid.helpers.EventGridPublisherClient", return_value=AsyncMock())
    async def test_update_status_and_publish_event_airlock_requestt_raises_503_if_publish_event_fails(self, event_grid_publisher_client_mock, airlock_request_repo_mock):
        airlock_request_mock = sample_airlock_request()
        updated_airlock_request_mock = sample_airlock_request_updated()
        airlock_request_repo_mock.update_airlock_request_status = MagicMock(return_value=updated_airlock_request_mock)
        event_grid_sender_client_mock = event_grid_publisher_client_mock.return_value
        event_grid_sender_client_mock.send = AsyncMock(side_effect=Exception)

        with pytest.raises(HTTPException) as ex:
            await update_status_and_publish_event_airlock_request(
                airlock_request=airlock_request_mock,
                airlock_request_repo=airlock_request_repo_mock,
                user=create_test_user(),
                new_status=AirlockRequestStatus.Submitted)
        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    async def test_save_airlock_review_saves_item(self, airlock_review_repo_mock):
        airlock_review_mock = sample_airlock_review()
        airlock_review_repo_mock.save_item = MagicMock(return_value=None)

        await save_airlock_review(
            airlock_review=airlock_review_mock,
            airlock_review_repo=airlock_review_repo_mock,
            user=create_test_user()
        )

        airlock_review_repo_mock.save_item.assert_called_once_with(airlock_review_mock)

    async def test_test_save_airlock_review_raises_503_if_save_to_db_fails(self, airlock_review_repo_mock):
        airlock_review_mock = sample_airlock_review()
        airlock_review_repo_mock.save_item = MagicMock(side_effect=Exception)
        with pytest.raises(HTTPException) as ex:
            await save_airlock_review(
                airlock_review=airlock_review_mock,
                airlock_review_repo=airlock_review_repo_mock,
                user=create_test_user()
            )

        assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
