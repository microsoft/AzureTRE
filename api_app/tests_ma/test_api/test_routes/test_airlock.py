import pytest
from mock import patch
from fastapi import status
from models.domain.airlock_review import AirlockReview, AirlockReviewDecision
from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from azure.core.exceptions import HttpResponseError
from resources import strings
from services.authentication import get_current_workspace_owner_or_researcher_user_or_tre_admin, get_current_workspace_owner_or_researcher_user, get_current_workspace_owner_user
pytestmark = pytest.mark.asyncio
WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "af89dccd-cdf8-4e47-8cfe-995faeac0f09"
AIRLOCK_REVIEW_ID = "11bd2526-054b-4305-a7f9-63a2d6d2a80c"


@pytest.fixture
def sample_airlock_request_input_data():
    return {
        "requestType": "import",
        "businessJustification": "some business justification"
    }


@pytest.fixture
def sample_airlock_review_input_data():
    return {
        "reviewDecision": "approved",
        "decisionExplanation": "the reason why this request was approved/rejected"
    }


def sample_airlock_request_object(status=AirlockRequestStatus.Draft, airlock_request_id=AIRLOCK_REQUEST_ID, workspace_id=WORKSPACE_ID):
    airlock_request = AirlockRequest(
        id=airlock_request_id,
        workspaceId=workspace_id,
        businessJustification="test business justification",
        requestType="import",
        status=status
    )
    return airlock_request


def sample_airlock_review_object():
    airlock_review = AirlockReview(
        id=AIRLOCK_REVIEW_ID,
        workspaceId=WORKSPACE_ID,
        requestId=AIRLOCK_REQUEST_ID,
        reviewDecision=AirlockReviewDecision.Approved,
        decisionExplanation="test explaination"
    )
    return airlock_review


class TestAirlockRoutesThatRequireOwnerOrResearcherRights():
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_researcher_user(self, app, researcher_user):
        # The following ws services requires the WS app registration
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_tre_admin] = researcher_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = researcher_user
        with patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object()), \
                patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation"), \
                patch("api.routes.airlock.AirlockRequestRepository.save_item"), \
                patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id"):
            yield
        app.dependency_overrides = {}

    # [POST] /workspaces/{workspace_id}/requests
    @patch("api.routes.airlock.save_and_publish_event_airlock_request")
    async def test_post_airlock_request_creates_airlock_request_returns_201(self, _, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["airlock_request"]["id"] == AIRLOCK_REQUEST_ID

    @patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", side_effect=ValueError)
    async def test_post_airlock_request_input_is_malformed_returns_400(self, _, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_post_airlock_request_with_non_deployed_workspace_id_returns_404(self, _, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.airlock.AirlockRequestRepository.save_item", side_effect=UnableToAccessDatabase)
    async def test_post_airlock_request_with_state_store_endpoint_not_responding_returns_503(self, _, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.delete_item")
    @patch("event_grid.helpers.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_airlock_request_with_event_grid_not_responding_returns_503(self, _, __, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    # [POST] /workspaces/{workspace_id}/requests/{airlock_request_id}/submit
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.update_status_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Submitted))
    async def test_post_submit_airlock_request_submitts_airlock_request_returns_200(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlock_request"]["id"] == AIRLOCK_REQUEST_ID
        assert response.json()["airlock_request"]["status"] == AirlockRequestStatus.Submitted

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=EntityDoesNotExist)
    async def test_post_submit_airlock_request_if_request_not_found_returns_404(self, _, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=UnableToAccessDatabase)
    @patch("api.routes.airlock.update_status_and_publish_event_airlock_request", side_effect=UnableToAccessDatabase)
    async def test_post_submit_airlock_request_with_state_store_endpoint_not_responding_returns_503(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.AirlockRequestRepository.update_airlock_request_status")
    @patch("api.routes.airlock.AirlockRequestRepository.delete_item")
    @patch("event_grid.helpers.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_submit_airlock_request_with_event_grid_not_responding_returns_503(self, _, __, ___, ____, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.AirlockRequestRepository._validate_status_update", return_value=False)
    async def test_post_submit_airlock_request_with_illegal_status_change_returns_400(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAirlockRoutesThatRequireOwnerRights():
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_researcher_user(self, app, owner_user):
        # The following ws services requires the WS app registration
        app.dependency_overrides[get_current_workspace_owner_user] = owner_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = owner_user
        with patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object()), \
                patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation"), \
                patch("api.routes.airlock.AirlockRequestRepository.save_item"), \
                patch("api.routes.airlock.AirlockReviewRepository.save_item"), \
                patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id"):
            yield
        app.dependency_overrides = {}

    # [POST] /workspaces/{workspace_id}/requests/{airlock_request_id}/review
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("api.routes.airlock.AirlockReviewRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("api.routes.airlock.update_status_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved))
    @patch("api.routes.airlock.AirlockReviewRepository.save_item")
    async def test_post_create_airlock_review_approves_airlock_request_returns_200(self, _, __, ___, ____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlock_review"]["id"] == AIRLOCK_REVIEW_ID
        assert response.json()["airlock_review"]["reviewDecision"] == AirlockReviewDecision.Approved

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("api.routes.airlock.AirlockReviewRepository.create_airlock_review_item", side_effect=ValueError)
    async def test_post_create_airlock_review_input_is_malformed_returns_400(self, _, __, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("api.routes.airlock.AirlockReviewRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("api.routes.airlock.AirlockReviewRepository.save_item", side_effect=UnableToAccessDatabase)
    async def test_post_create_airlock_review_with_state_store_endpoint_not_responding_returns_503(self, _, __, ___, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("api.routes.airlock.AirlockReviewRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("api.routes.airlock.AirlockReviewRepository.save_item")
    @patch("api.routes.airlock.AirlockRequestRepository.update_airlock_request_status")
    @patch("event_grid.helpers.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_create_airlock_review_with_event_grid_not_responding_returns_503(self, _, __, ___, ____, _____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("api.routes.airlock.AirlockReviewRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("api.routes.airlock.AirlockReviewRepository.save_item")
    @patch("api.routes.airlock.AirlockRequestRepository._validate_status_update", return_value=False)
    async def test_post_create_airlock_review_with_illegal_status_change_returns_400(self, _, __, ___, ____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
