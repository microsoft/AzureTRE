import pytest
from mock import patch
from azure.eventgrid import EventGridEvent
from fastapi import status
from db.errors import EntityDoesNotExist, UnableToAccessDatabase
from models.domain.workspace import Workspace
from models.domain.airlock_request import AirlockRequest
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP
from tests_ma.test_api.conftest import create_admin_user
from azure.core.exceptions import HttpResponseError

from resources import strings
from services.authentication import get_current_workspace_owner_or_researcher_user, get_current_workspace_owner_or_researcher_user_or_tre_admin


pytestmark = pytest.mark.asyncio


WORKSPACE_ID = '933ad738-7265-4b5f-9eae-a1a62928772e'
AIRLOCK_REQUEST_ID = 'a33ad738-7265-4b5f-9eae-a1a62928772a'
CLIENT_ID = 'f0acf127-a672-a672-a672-a15e5bf9f127'


@pytest.fixture
def sample_airlock_request_input_data():
    return {
        "requestType": "import",
        "businessJustification": "some business justification"
    }


def sample_status_changed_event(airlock_request_id=AIRLOCK_REQUEST_ID, workspace_id=WORKSPACE_ID):
    eventgrid_event = EventGridEvent(
        event_type="statusChanged",
        data={
            "request_id": airlock_request_id,
            "status": "draft",
            "type": "import",
            "workspace_id": workspace_id[:-4]
        },
        subject=f"{airlock_request_id}/statusChanged",
        data_version="2.0"
    )
    return eventgrid_event


def sample_airlock_request_object(airlock_request_id=AIRLOCK_REQUEST_ID, workspace_id=WORKSPACE_ID):
    airlock_request = AirlockRequest(
        id=airlock_request_id,
        workspaceId=workspace_id,
        businessJustification="test business justification",
        requestType="import"
    )

    return airlock_request


def sample_workspace(workspace_id=WORKSPACE_ID, auth_info: dict = {}) -> Workspace:
    workspace = Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={
            "client_id": "12345"
        },
        resourcePath=f'/workspaces/{workspace_id}',
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_admin_user()
    )
    if auth_info:
        workspace.properties = {**auth_info}
    return workspace


class TestAirlockRoutesThatRequireOwnerOrResearcherRights():
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_researcher_user(self, app, researcher_user):
        # The following ws services requires the WS app registration
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_tre_admin] = researcher_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = researcher_user
        yield
        app.dependency_overrides = {}

    # [POST] /workspaces/{workspace_id}/requests
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.airlock.save_and_publish_event_airlock_request")
    @patch("api.routes.airlock.AirlockRequestRepository.save_item")
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object())
    async def test_post_airlock_request_creates_airlock_request(self, _, __, ___, ____, get_workspace_mock, app, client, sample_airlock_request_input_data):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["airlock_request"]["id"] == AIRLOCK_REQUEST_ID

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", side_effect=ValueError)
    async def test_post_airlock_request_raises_400_bad_request_if_input_is_bad(self, _, __, get_workspace_mock, app, client, sample_airlock_request_input_data):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    async def test_post_airlock_request_with_non_deployed_workspace_id_returns_404(self, _, __, app, client, sample_airlock_request_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.airlock.AirlockRequestRepository.save_item", side_effect=UnableToAccessDatabase)
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object())
    async def test_post_airlock_request_with_state_store_endpoint_not_responding_returns_503(self, _, __, ___, get_workspace_mock, app, client, sample_airlock_request_input_data):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.airlock.AirlockRequestRepository.delete_item")
    @patch("event_grid.helpers.send_status_changed_event", side_effect=HttpResponseError)
    @patch("api.routes.airlock.AirlockRequestRepository.save_item")
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.airlock.AirlockRequestRepository.create_airlock_request_item", return_value=sample_airlock_request_object())
    async def test_post_airlock_request_with_event_grid_not_responding_returns_503(self, _, __, ___, ____, _____, get_workspace_mock, app, client, sample_airlock_request_input_data):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_AIRLOCK_REQUEST, workspace_id=WORKSPACE_ID), json=sample_airlock_request_input_data)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# TODO Submit Airlock Request
# TODO  Submit Airlock Request fails becuase of saving the item
# TODO Submit Airlock Request fails becuase of Eventgrid message publish failed
# TODO Submit Airlock Request fails becuase already submitted

