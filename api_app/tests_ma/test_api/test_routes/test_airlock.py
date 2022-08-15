import pytest
from mock import patch
from fastapi import status
from models.domain.airlock_review import AirlockReview, AirlockReviewDecision
from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus
from azure.core.exceptions import HttpResponseError

from models.domain.workspace import Workspace
from resources import strings
from services.authentication import get_current_workspace_owner_or_researcher_user, get_current_workspace_owner_or_researcher_user_or_airlock_manager, get_current_airlock_manager_user
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


class TestAirlockRoutesThatRequireOwnerOrResearcherRights():
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_researcher_user(self, app, researcher_user):
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = researcher_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = researcher_user
        with patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object()), \
                patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation"), \
                patch("api.routes.airlock.AirlockRequestRepository.save_item"), \
                patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id"), \
                patch("services.aad_authentication.AzureADAuthorization.get_workspace_role_assignment_details", return_value={"researcher_emails": ["researcher@outlook.com"], "owner_emails": ["owner@outlook.com"]}):
            yield
        app.dependency_overrides = {}

    # [GET] /workspaces/{workspace_id}/requests}
    @patch("api.routes.airlock.AirlockRequestRepository.get_airlock_requests", return_value=[])
    async def test_get_all_airlock_requests_by_workspace_returns_200(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_AIRLOCK_REQUESTS, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_200_OK

    # [POST] /workspaces/{workspace_id}/requests
    @patch("api.routes.airlock.save_and_publish_event_airlock_request")
    async def test_post_airlock_request_creates_airlock_request_returns_201(self, _, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["airlockRequest"]["id"] == AIRLOCK_REQUEST_ID

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
    @patch("event_grid.event_sender.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_airlock_request_with_event_grid_not_responding_returns_503(self, _, __, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace(workspace_properties={"enable_airlock": False}))
    async def test_post_airlock_request_with_airlock_disabled_returns_405(self, _, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace(workspace_properties={}))
    @patch("api.routes.airlock.save_and_publish_event_airlock_request")
    async def test_post_airlock_request_with_enable_airlock_property_missing_returns_201(self, _, __, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_201_CREATED

    # [GET] /workspaces/{workspace_id}/requests/{airock_request_id}
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    async def test_get_airlock_request_returns_200(self, _, app, client):
        airlock_request = sample_airlock_request_object()
        response = await client.get(app.url_path_for(strings.API_GET_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlockRequest"]["id"] == airlock_request.id

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=CosmosResourceNotFoundError)
    async def test_get_airlock_request_no_airlock_request_found_returns_404(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=UnableToAccessDatabase)
    async def test_get_airlock_request_state_store_endpoint_not_responding_returns_503(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    # [POST] /workspaces/{workspace_id}/requests/{airlock_request_id}/submit
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.update_status_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Submitted))
    async def test_post_submit_airlock_request_submitts_airlock_request_returns_200(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlockRequest"]["id"] == AIRLOCK_REQUEST_ID
        assert response.json()["airlockRequest"]["status"] == AirlockRequestStatus.Submitted

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
    @patch("event_grid.event_sender.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_submit_airlock_request_with_event_grid_not_responding_returns_503(self, _, __, ___, ____, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.AirlockRequestRepository.validate_status_update", return_value=False)
    async def test_post_submit_airlock_request_with_illegal_status_change_returns_400(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [POST] /workspaces/{workspace_id}/requests/{airlock_request_id}/cancel
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.update_status_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Cancelled))
    async def test_post_cancel_airlock_request_canceles_request_returns_200(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_CANCEL_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlockRequest"]["id"] == AIRLOCK_REQUEST_ID
        assert response.json()["airlockRequest"]["status"] == AirlockRequestStatus.Cancelled

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=EntityDoesNotExist)
    async def test_post_cancel_airlock_request_if_request_not_found_returns_404(self, _, app, client):
        response = await client.post(app.url_path_for(strings.API_CANCEL_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=CosmosResourceNotFoundError)
    @patch("api.routes.airlock.validate_user_allowed_to_access_storage_account")
    async def test_get_airlock_container_link_no_airlock_request_found_returns_404(self, _, __, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", side_effect=EntityDoesNotExist)
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.validate_user_allowed_to_access_storage_account")
    async def test_get_airlock_container_link_no_workspace_request_found_returns_404(self, _, __, ___, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id",
           return_value=sample_airlock_request_object(status=AirlockRequestStatus.ApprovalInProgress))
    async def test_get_airlock_container_link_in_progress_request_returns_400(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id",
           return_value=sample_airlock_request_object(status=AirlockRequestStatus.Cancelled))
    async def test_get_airlock_container_link_cancelled_request_returns_400(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id",
           return_value=sample_workspace(WORKSPACE_ID))
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved))
    @patch("api.routes.airlock.validate_user_allowed_to_access_storage_account")
    @patch("api.routes.airlock.get_airlock_request_container_sas_token", return_value="valid-sas-token")
    async def test_get_airlock_container_link_returned_as_expected(self, get_airlock_request_container_sas_token_mock, __, ___, ____, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["containerUrl"] == get_airlock_request_container_sas_token_mock.return_value


class TestAirlockRoutesThatRequireAirlockManagerRights():
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_airlock_manager_user(self, app, airlock_manager_user):
        app.dependency_overrides[get_current_airlock_manager_user] = airlock_manager_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = airlock_manager_user
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
    @patch("event_grid.event_sender.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_create_airlock_review_with_event_grid_not_responding_returns_503(self, _, __, ___, ____, _____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("api.routes.airlock.AirlockReviewRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("api.routes.airlock.AirlockReviewRepository.save_item")
    @patch("api.routes.airlock.AirlockRequestRepository.validate_status_update", return_value=False)
    async def test_post_create_airlock_review_with_illegal_status_change_returns_400(self, _, __, ___, ____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
