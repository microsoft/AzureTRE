import time
import pytest
import pytest_asyncio
from mock import patch
from fastapi import status
from azure.core.exceptions import HttpResponseError
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from tests_ma.test_api.conftest import create_test_user, get_required_roles
from api.routes.airlock import create_draft_request
from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from models.domain.airlock_request import AirlockRequest, AirlockRequestStatus, AirlockReview, AirlockReviewDecision, AirlockReviewUserResource
from models.domain.user_resource import UserResource
from models.domain.resource_template import ResourceTemplate
from models.domain.workspace_service import WorkspaceService
from models.domain.workspace import Workspace
from models.domain.operation import Operation
from resources import strings
from services.authentication import get_current_workspace_owner_or_researcher_user, get_current_workspace_owner_or_researcher_user_or_airlock_manager, get_current_airlock_manager_user
pytestmark = pytest.mark.asyncio


WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
IMPORT_WORKSPACE_ID = "cba000d3-13da-58fc-b6e9-9a7853ef753e"
WORKSPACE_SERVICE_ID = "ca8fec6b-3d90-4ad3-a003-77daddfc2d64"
USER_RESOURCE_ID = "a6489dfe-625e-4e8e-a3dc-8eda79f0f081"

AIRLOCK_REQUEST_ID = "af89dccd-cdf8-4e47-8cfe-995faeac0f09"
AIRLOCK_REVIEW_ID = "11bd2526-054b-4305-a7f9-63a2d6d2a80c"


@pytest.fixture
def sample_airlock_request_input_data():
    return {
        "type": "import",
        "businessJustification": "some business justification"
    }


@pytest.fixture
def sample_airlock_review_input_data():
    return {
        "reviewDecision": "approved",
        "decisionExplanation": "the reason why this request was approved/rejected"
    }


def sample_airlock_request_object(status=AirlockRequestStatus.Draft, airlock_request_id=AIRLOCK_REQUEST_ID, workspace_id=WORKSPACE_ID, reviews: bool = False, review_user_resource: bool = False):
    airlock_request = AirlockRequest(
        id=airlock_request_id,
        workspaceId=workspace_id,
        title="test title",
        businessJustification="test business justification",
        type="import",
        status=status,
        reviews=[sample_airlock_review_object()] if reviews else None,
        reviewUserResources={"user-guid-here": sample_airlock_user_resource_object()} if review_user_resource else {}
    )
    return airlock_request


def sample_airlock_review_object():
    airlock_review = AirlockReview(
        id=AIRLOCK_REVIEW_ID,
        dateCreated=1660231576.328734,
        reviewDecision=AirlockReviewDecision.Approved,
        decisionExplanation="test explaination"
    )
    return airlock_review


def sample_airlock_user_resource_object():
    return AirlockReviewUserResource(
        workspaceId=WORKSPACE_ID,
        workspaceServiceId=WORKSPACE_SERVICE_ID,
        userResourceId=USER_RESOURCE_ID
    )


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


def sample_airlock_review_config() -> dict:
    return {
        "airlock_review_config": {
            "import": {
                "import_vm_workspace_id": IMPORT_WORKSPACE_ID,
                "import_vm_workspace_service_id": WORKSPACE_SERVICE_ID,
                "import_vm_user_resource_template_name": "tre-service-guacamole-import-reviewvm"
            },
            "export": {
                "export_vm_workspace_service_id": WORKSPACE_SERVICE_ID,
                "export_vm_user_resource_template_name": "tre-service-guacamole-export-reviewvm"
            }
        }
    }


def sample_review_resource(healthy=True) -> UserResource:
    resource = UserResource(
        id=USER_RESOURCE_ID,
        templateName="test",
        templateVersion="0.0.1",
        _etag="123",
        isEnabled=True,
        properties={"azure_resource_id": "abc"},
        deploymentStatus="deployed" if healthy else "failed"
    )
    return resource


def create_test_user_with_roles(roles):
    def inner():
        user = create_test_user()
        user.roles = roles
        return user
    return inner


class TestAirlockRoutesThatRequireOwnerOrResearcherRights():
    @pytest_asyncio.fixture(autouse=True, scope='class')
    def log_in_with_researcher_user(self, app, researcher_user):
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = researcher_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = researcher_user
        with patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object()), \
                patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation"), \
                patch("api.routes.airlock.AirlockRequestRepository.save_item"), \
                patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id"), \
                patch("services.aad_authentication.AzureADAuthorization.get_workspace_user_emails_by_role_assignment", return_value={"WorkspaceResearcher": ["researcher@outlook.com"], "WorkspaceOwner": ["owner@outlook.com"], "AirlockManager": ["manager@outlook.com"]}):
            yield
        app.dependency_overrides = {}

    # [GET] /workspaces/{workspace_id}/requests}
    @patch("api.routes.airlock.AirlockRequestRepository.get_airlock_requests", return_value=[])
    async def test_get_all_airlock_requests_by_workspace_returns_200(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_LIST_AIRLOCK_REQUESTS, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_200_OK

    # [POST] /workspaces/{workspace_id}/requests
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace(workspace_properties={}))
    @patch("api.routes.airlock.save_and_publish_event_airlock_request")
    async def test_post_airlock_request_creates_airlock_request_returns_201(self, _, __, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["airlockRequest"]["id"] == AIRLOCK_REQUEST_ID

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace(workspace_properties={}))
    @patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", side_effect=ValueError)
    async def test_post_airlock_request_input_is_malformed_returns_400(self, _, __, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_post_airlock_request_with_non_deployed_workspace_id_returns_404(self, _, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace(workspace_properties={}))
    @patch("api.routes.airlock.AirlockRequestRepository.save_item", side_effect=UnableToAccessDatabase)
    async def test_post_airlock_request_with_state_store_endpoint_not_responding_returns_503(self, _, __, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace(workspace_properties={}))
    @patch("api.routes.airlock.AirlockRequestRepository.delete_item")
    @patch("event_grid.event_sender.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_airlock_request_with_event_grid_not_responding_returns_503(self, _, __, ___, app, client, sample_airlock_request_input_data):
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
    @patch("api.routes.airlock.update_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Submitted))
    async def test_post_submit_airlock_request_submits_airlock_request_returns_200(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlockRequest"]["id"] == AIRLOCK_REQUEST_ID
        assert response.json()["airlockRequest"]["status"] == AirlockRequestStatus.Submitted

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=EntityDoesNotExist)
    async def test_post_submit_airlock_request_if_request_not_found_returns_404(self, _, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=UnableToAccessDatabase)
    @patch("api.routes.airlock.update_and_publish_event_airlock_request", side_effect=UnableToAccessDatabase)
    async def test_post_submit_airlock_request_with_state_store_endpoint_not_responding_returns_503(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_SUBMIT_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("api.routes.airlock.AirlockRequestRepository.update_airlock_request")
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
    @patch("services.airlock.update_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Cancelled))
    async def test_post_cancel_airlock_request_cancels_request_returns_200(self, _, __, app, client):
        response = await client.post(app.url_path_for(strings.API_CANCEL_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlockRequest"]["id"] == AIRLOCK_REQUEST_ID
        assert response.json()["airlockRequest"]["status"] == AirlockRequestStatus.Cancelled

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=EntityDoesNotExist)
    async def test_post_cancel_airlock_request_if_request_not_found_returns_404(self, _, app, client):
        response = await client.post(app.url_path_for(strings.API_CANCEL_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", side_effect=CosmosResourceNotFoundError)
    @patch("services.airlock.validate_user_allowed_to_access_storage_account")
    async def test_get_airlock_container_link_no_airlock_request_found_returns_404(self, _, __, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", side_effect=EntityDoesNotExist)
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object())
    @patch("services.airlock.validate_user_allowed_to_access_storage_account")
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

    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id",
           return_value=sample_airlock_request_object(status=AirlockRequestStatus.Revoked))
    async def test_get_airlock_container_link_revoked_request_returns_400(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id",
           return_value=sample_workspace(WORKSPACE_ID))
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved))
    @patch("services.airlock.validate_user_allowed_to_access_storage_account")
    @patch("services.airlock.get_airlock_request_container_sas_token", return_value="valid-sas-token")
    async def test_get_airlock_container_link_returned_as_expected(self, get_airlock_request_container_sas_token_mock, __, ___, ____, app, client):
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID,
                                                     airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["containerUrl"] == get_airlock_request_container_sas_token_mock.return_value


class TestAirlockRoutesThatRequireAirlockManagerRights():
    @pytest_asyncio.fixture(autouse=True, scope='class')
    def log_in_with_airlock_manager_user(self, app, airlock_manager_user):
        app.dependency_overrides[get_current_airlock_manager_user] = airlock_manager_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = airlock_manager_user
        with patch("services.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object()), \
                patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation"), \
                patch("services.airlock.AirlockRequestRepository.save_item"), \
                patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id"):
            yield
        app.dependency_overrides = {}

    # [POST] /workspaces/{workspace_id}/requests/{airlock_request_id}/review
    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("services.airlock.AirlockRequestRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("services.airlock.update_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved, reviews=True))
    @patch("services.airlock.AirlockRequestRepository.save_item")
    async def test_post_create_airlock_review_approves_airlock_request_returns_200(self, _, __, ___, ____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlockRequest"]["reviews"][0]["id"] == AIRLOCK_REVIEW_ID
        assert response.json()["airlockRequest"]["reviews"][0]["reviewDecision"] == AirlockReviewDecision.Approved

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("services.airlock.AirlockRequestRepository.create_airlock_review_item", side_effect=ValueError)
    async def test_post_create_airlock_review_input_is_malformed_returns_400(self, _, __, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("services.airlock.AirlockRequestRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("services.airlock.AirlockRequestRepository.save_item")
    @patch("services.airlock.AirlockRequestRepository.update_airlock_request")
    @patch("event_grid.event_sender.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_create_airlock_review_with_event_grid_not_responding_returns_503(self, _, __, ___, ____, _____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("services.airlock.AirlockRequestRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("services.airlock.AirlockRequestRepository.save_item")
    @patch("services.airlock.AirlockRequestRepository.validate_status_update", return_value=False)
    async def test_post_create_airlock_review_with_illegal_status_change_returns_400(self, _, __, ___, ____, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("services.airlock.send_uninstall_message")
    @patch("services.airlock.ResourceHistoryRepository.save_item")
    @patch("services.airlock.UserResourceRepository.update_item_with_etag")
    @patch("services.airlock.update_user_resource")
    @patch("services.airlock.ResourceTemplateRepository.get_template_by_name_and_version", return_value=ResourceTemplate(name="test_template", id="123", description="test", version="0.0.1", resourceType="user-resource", current=True, required=[], properties={}))
    @patch("services.airlock.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=WorkspaceService(id=WORKSPACE_SERVICE_ID, templateName="test", templateVersion="0.0.1", _etag="123"))
    @patch("services.airlock.UserResourceRepository.get_user_resource_by_id", return_value=UserResource(id=USER_RESOURCE_ID, templateName="test", templateVersion="0.0.1", _etag="123"))
    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview, review_user_resource=True))
    @patch("services.airlock.AirlockRequestRepository.create_airlock_review_item", return_value=sample_airlock_review_object())
    @patch("services.airlock.update_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved, review_user_resource=True))
    @patch("services.airlock.AirlockRequestRepository.save_item")
    async def test_post_create_airlock_review_cleans_up_review_user_resources(self, _, __, ___, ____, _____, ______, _______, ________, _________, __________, send_uninstall_message_mock, app, client, sample_airlock_review_input_data):
        response = await client.post(app.url_path_for(strings.API_REVIEW_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=sample_airlock_review_input_data)
        assert response.status_code == status.HTTP_200_OK
        assert send_uninstall_message_mock.call_count == 1

    @patch("services.airlock.save_and_deploy_resource", return_value=Operation(id="123", resourceId=USER_RESOURCE_ID, resourcePath="a/b", action="install", createdWhen=time.time(), updatedWhen=time.time()))
    @patch("services.airlock.update_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview, review_user_resource=True))
    @patch("services.airlock.get_airlock_container_link", return_value="http://test-sas")
    @patch("services.airlock.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=WorkspaceService(id=WORKSPACE_SERVICE_ID, templateName="test", templateVersion="0.0.1", _etag="123"))
    @patch("services.airlock.UserResourceRepository.create_user_resource_item", return_value=(UserResource(id=USER_RESOURCE_ID, templateName="test", templateVersion="0.0.1", _etag="123"), "test"))
    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", return_value=sample_workspace(workspace_properties=sample_airlock_review_config()))
    async def test_post_create_review_user_resource_returns_200(self, _, __, ___, ____, _____, ______, _______, app, client):
        # Check the Airlock Request has been updated with VM information
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_202_ACCEPTED

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview, review_user_resource=True))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", return_value=sample_workspace(workspace_properties={"airlock_review_config": "invalid_configuration"}))
    async def test_post_create_review_user_resource_returns_422_if_configuration_invalid(self, _, __, app, client):
        # Check the Airlock Request has been updated with VM information
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("services.airlock.WorkspaceServiceRepository.get_workspace_service_by_id", side_effect=EntityDoesNotExist)
    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview, review_user_resource=True))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", return_value=sample_workspace(workspace_properties={"airlock_review_config": "invalid_configuration"}))
    async def test_post_create_review_user_resource_returns_422_if_cannot_find_workspace_service(self, _, __, ___, app, client):
        # Check the Airlock Request has been updated with VM information
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Draft))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", return_value=sample_workspace())
    async def test_post_create_review_user_resource_returns_400_if_request_is_not_in_review(self, _, __, app, client):
        # Check the Airlock Request has been updated with VM information
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("services.airlock.get_azure_resource_status", return_value={"powerState": "VM running"})
    @patch("services.airlock.ResourceTemplateRepository.get_template_by_name_and_version", return_value=ResourceTemplate(name="test_template", id="123", description="test", version="0.0.1", resourceType="user-resource", current=True, required=[], properties={}))
    @patch("services.airlock.UserResourceRepository.get_user_resource_by_id", return_value=sample_review_resource())
    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview, review_user_resource=True))
    @patch("services.airlock.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=WorkspaceService(id=WORKSPACE_SERVICE_ID, templateName="test", templateVersion="0.0.1", _etag="123"))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", return_value=sample_workspace(workspace_properties=sample_airlock_review_config()))
    async def test_post_create_review_user_resource_with_existing_healthy_resource_returns_409(self, _, __, ___, ____, _____, ______, app, client):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_409_CONFLICT

    @patch("services.airlock.delete_review_user_resource", return_value=Operation(id="123", resourceId=USER_RESOURCE_ID, resourcePath="a/b", action="uninstall", createdWhen=time.time(), updatedWhen=time.time()))
    @patch("services.airlock.save_and_deploy_resource", return_value=Operation(id="123", resourceId=USER_RESOURCE_ID, resourcePath="a/b", action="install", createdWhen=time.time(), updatedWhen=time.time()))
    @patch("services.airlock.get_azure_resource_status", return_value={})
    @patch("services.airlock.UserResourceRepository.get_user_resource_by_id", return_value=sample_review_resource(healthy=False))
    @patch("services.airlock.update_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview, review_user_resource=True))
    @patch("services.airlock.get_airlock_container_link", return_value="http://test-sas")
    @patch("services.airlock.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=WorkspaceService(id=WORKSPACE_SERVICE_ID, templateName="test", templateVersion="0.0.1", _etag="123"))
    @patch("services.airlock.UserResourceRepository.create_user_resource_item", return_value=(UserResource(id=USER_RESOURCE_ID, templateName="test", templateVersion="0.0.1", _etag="123"), "test"))
    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.InReview, review_user_resource=True))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", return_value=sample_workspace(workspace_properties=sample_airlock_review_config()))
    async def test_post_create_review_user_resource_with_existing_unhealthy_resource_deletes_previous_and_redeploys(self, _, __, ___, ____, _____, ______, _______, ________, deploy_resource_mock, delete_review_resource_mock, app, client):
        await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REVIEW_USER_RESOURCE, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert delete_review_resource_mock.call_count == 1
        assert deploy_resource_mock.call_count == 1

    # [POST] /workspaces/{workspace_id}/requests/{airlock_request_id}/revoke
    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved))
    @patch("services.airlock.update_and_publish_event_airlock_request", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Revoked))
    async def test_post_revoke_airlock_request_revokes_request_returns_200(self, _, __, app, client):
        reason_data = {"reason": "Test revocation reason"}
        response = await client.post(app.url_path_for(strings.API_REVOKE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=reason_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["airlockRequest"]["id"] == AIRLOCK_REQUEST_ID
        assert response.json()["airlockRequest"]["status"] == AirlockRequestStatus.Revoked

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", side_effect=EntityDoesNotExist)
    async def test_post_revoke_airlock_request_if_request_not_found_returns_404(self, _, app, client):
        reason_data = {"reason": "Test revocation reason"}
        response = await client.post(app.url_path_for(strings.API_REVOKE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=reason_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved))
    @patch("services.airlock.AirlockRequestRepository.validate_status_update", return_value=False)
    async def test_post_revoke_airlock_request_with_illegal_status_change_returns_400(self, _, __, app, client):
        reason_data = {"reason": "Test revocation reason"}
        response = await client.post(app.url_path_for(strings.API_REVOKE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=reason_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved))
    @patch("services.airlock.AirlockRequestRepository.update_airlock_request")
    @patch("services.airlock.AirlockRequestRepository.delete_item")
    @patch("event_grid.event_sender.send_status_changed_event", side_effect=HttpResponseError)
    async def test_post_revoke_airlock_request_with_event_grid_not_responding_returns_503(self, _, __, ___, ____, app, client):
        reason_data = {"reason": "Test revocation reason"}
        response = await client.post(app.url_path_for(strings.API_REVOKE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json=reason_data)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("services.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Approved))
    async def test_post_revoke_airlock_request_missing_reason_returns_422(self, _, app, client):
        response = await client.post(app.url_path_for(strings.API_REVOKE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID), json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAirlockRoutesPermissions():

    @pytest_asyncio.fixture()
    def log_in_with_user(self, app):
        def inner(user):
            app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = user
            app.dependency_overrides[get_current_airlock_manager_user] = user
            app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = user
        return inner

    @pytest.mark.parametrize("role", (role for role in get_required_roles(endpoint=create_draft_request)))
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace(WORKSPACE_ID))
    @patch("api.routes.airlock.AirlockRequestRepository.read_item_by_id", return_value=sample_airlock_request_object(status=AirlockRequestStatus.Draft))
    @patch("services.airlock.get_airlock_request_container_sas_token", return_value="valid-sas-token")
    async def test_get_airlock_container_link_is_accessible_to_every_role_that_can_create_request(self, _, __, ___, ____, app, client, log_in_with_user, role):
        user = create_test_user_with_roles([role])
        log_in_with_user(user)
        response = await client.get(app.url_path_for(strings.API_AIRLOCK_REQUEST_LINK, workspace_id=WORKSPACE_ID, airlock_request_id=AIRLOCK_REQUEST_ID))
        assert response.status_code == status.HTTP_200_OK
