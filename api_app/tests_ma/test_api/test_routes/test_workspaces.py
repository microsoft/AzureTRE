import random
from unittest.mock import AsyncMock
import uuid
from pydantic import Field
import pytest
from mock import patch

from fastapi import status
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP, FAKE_UPDATE_TIMESTAMP
from tests_ma.test_api.conftest import create_admin_user, create_test_user, create_workspace_owner_user, create_workspace_researcher_user

from models.domain.resource_template import ResourceTemplate
from models.schemas.operation import OperationInResponse

from db.errors import EntityDoesNotExist
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.domain.authentication import RoleAssignment
from models.domain.operation import Operation, OperationStep, Status
from models.domain.resource import ResourceHistoryItem, ResourceType
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace, WorkspaceRole
from models.domain.workspace_service import WorkspaceService
from resources import strings
from models.schemas.resource_template import ResourceTemplateInformation
from services.authentication import get_current_admin_user, \
    get_current_tre_user_or_tre_admin, get_current_workspace_owner_user, \
    get_current_workspace_owner_or_researcher_user, \
    get_current_workspace_owner_or_researcher_user_or_airlock_manager, \
    get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin, \
    get_current_workspace_owner_or_airlock_manager
from azure.cosmos.exceptions import CosmosAccessConditionFailedError


pytestmark = pytest.mark.asyncio


WORKSPACE_ID = '933ad738-7265-4b5f-9eae-a1a62928772e'
SERVICE_ID = 'abcad738-7265-4b5f-9eae-a1a62928772e'
USER_RESOURCE_ID = 'a33ad738-7265-4b5f-9eae-a1a62928772a'
CLIENT_ID = 'f0acf127-a672-a672-a672-a15e5bf9f127'
OPERATION_ID = '11111111-7265-4b5f-9eae-a1a62928772f'


@pytest.fixture
def workspace_input():
    return {
        "templateName": "test-workspace",
        "properties": {
            "display_name": "display",
            "client_id": CLIENT_ID
        }
    }


@pytest.fixture
def workspace_service_input():
    return {
        "templateName": "test-workspace-service",
        "properties": {
            "display_name": "display"
        }
    }


@pytest.fixture
def sample_user_resource_input_data():
    return {
        "templateName": "test-user-resource",
        "properties": {
            "display_name": "display",
        }
    }


@pytest.fixture
def disabled_workspace() -> Workspace:
    workspace = sample_workspace(WORKSPACE_ID)
    workspace.isEnabled = False
    return workspace


def sample_workspace(workspace_id=WORKSPACE_ID, auth_info: dict = {}) -> Workspace:
    workspace = Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={
            "client_id": "12345",
            "scope_id": "test_scope_id",
            "sp_id": "test_sp_id"
        },
        resourcePath=f'/workspaces/{workspace_id}',
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_admin_user()
    )
    if auth_info:
        workspace.properties = {**auth_info}
    return workspace


def sample_resource_history(history_length, resource_id) -> ResourceHistoryItem:
    resource_history = []
    user = create_test_user()

    for version in range(history_length):
        resource_history_item = ResourceHistoryItem(
            id=str(uuid.uuid4()),
            resourceId=resource_id,
            isEnabled=True,
            resourceVersion=version,
            templateVersion="template_version",
            properties={
                'display_name': 'initial display name',
                'description': 'initial description',
                'computed_prop': 'computed_val'
            },
            updatedWhen=FAKE_CREATE_TIMESTAMP,
            user=user
        )
        resource_history.append(resource_history_item)
    return resource_history


def sample_resource_operation(resource_id: str, operation_id: str):
    operation = Operation(
        id=operation_id,
        resourceId=resource_id,
        resourcePath=f'/workspaces/{resource_id}',
        resourceVersion=0,
        action="install",
        message="test",
        Status=Status.Deployed,
        createdWhen=FAKE_UPDATE_TIMESTAMP,
        updatedWhen=FAKE_UPDATE_TIMESTAMP,
        user=create_test_user(),
        steps=[
            OperationStep(
                id="random-uuid",
                templateStepId="main",
                resourceId=resource_id,
                resourceAction="install",
                updatedWhen=FAKE_UPDATE_TIMESTAMP,
                sourceTemplateResourceId=resource_id
            )
        ]
    )
    return operation


def sample_resource_operation_in_response(resource_id: str, operation_id: str):
    op = sample_resource_operation(resource_id=resource_id, operation_id=operation_id)
    return OperationInResponse(operation=op)


def sample_deployed_workspace(workspace_id=WORKSPACE_ID, authInfo={}):
    workspace = Workspace(
        id=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={},
        resourcePath="test",
        updatedWhen=FAKE_CREATE_TIMESTAMP
    )
    if authInfo:
        workspace.properties = {**authInfo}
    return workspace


def sample_workspace_service(workspace_service_id=SERVICE_ID, workspace_id=WORKSPACE_ID):
    return WorkspaceService(
        id=workspace_service_id,
        workspaceId=workspace_id,
        templateName="tre-workspace-base",
        templateVersion="0.1.0",
        etag="",
        properties={},
        resourcePath=f'/workspaces/{workspace_id}/workspace-services/{workspace_service_id}',
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_workspace_owner_user()
    )


def sample_user_resource_object(user_resource_id=USER_RESOURCE_ID, workspace_id=WORKSPACE_ID, parent_workspace_service_id=SERVICE_ID):
    user_resource = UserResource(
        id=user_resource_id,
        workspaceId=workspace_id,
        parentWorkspaceServiceId=parent_workspace_service_id,
        templateName="tre-user-resource",
        templateVersion="0.1.0",
        etag="",
        properties={},
        resourcePath=f'/workspaces/{workspace_id}/workspace-services/{parent_workspace_service_id}/user-resources/{user_resource_id}',
        updatedWhen=FAKE_CREATE_TIMESTAMP,
        user=create_workspace_researcher_user()
    )

    return user_resource


def sample_resource_template() -> ResourceTemplate:
    return ResourceTemplate(id="123",
                            name="tre-user-resource",
                            description="description",
                            version="0.1.0",
                            resourceType=ResourceType.UserResource,
                            current=True,
                            required=['os_image', 'title'],
                            properties={
                                'title': {
                                    'type': 'string',
                                    'title': 'Title of the resource'
                                },
                                'os_image': {
                                    'type': 'string',
                                    'title': 'Windows image',
                                    'description': 'Select Windows image to use for VM',
                                    'enum': [
                                        'Windows 10',
                                        'Server 2019 Data Science VM'
                                    ],
                                    'updateable': False
                                },
                                'vm_size': {
                                    'type': 'string',
                                    'title': 'Windows image',
                                    'description': 'Select Windows image to use for VM',
                                    'enum': [
                                        'small',
                                        'large'
                                    ],
                                    'updateable': True
                                }
                            },
                            actions=[])


def disabled_workspace_service():
    return WorkspaceService(id=SERVICE_ID, templateName='template name', templateVersion='1.0', etag="", isEnabled=False, properties={}, resourcePath="test")


def disabled_user_resource():
    return UserResource(id=USER_RESOURCE_ID, templateName='template name', templateVersion='1.0', etag="", isEnabled=False, properties={}, resourcePath="test")


class TestWorkspaceRoutesThatDontRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_non_admin_user(self, app, non_admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=non_admin_user()):
            yield

    # [GET] /workspaces
    @patch("api.routes.workspaces.WorkspaceRepository.get_active_workspaces")
    @patch("api.routes.workspaces.get_identity_role_assignments", return_value=[])
    async def test_get_workspaces_returns_empty_list_when_no_resources_exist(self, access_service_mock, get_workspaces_mock, app, client) -> None:
        get_workspaces_mock.return_value = []
        access_service_mock.get_workspace_role.return_value = [WorkspaceRole.Owner]

        response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
        assert response.json() == {"workspaces": []}

    # [GET] /workspaces
    @patch("api.routes.workspaces.WorkspaceRepository.get_active_workspaces")
    @patch("api.routes.workspaces.get_identity_role_assignments")
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_workspaces_returns_correct_data_when_resources_exist(self, _, access_service_mock, get_workspaces_mock, app, client) -> None:
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'app_role_id_workspace_owner': 'ab124', 'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
        auth_info_user_in_workspace_researcher_role = {'sp_id': 'ab123', 'app_role_id_workspace_owner': 'ab127', 'app_role_id_workspace_researcher': 'ab126', 'app_role_id_workspace_airlock_manager': 'ab130'}
        auth_info_user_not_in_workspace_role = {'sp_id': 'ab127', 'app_role_id_workspace_owner': 'ab128', 'app_role_id_workspace_researcher': 'ab129', 'app_role_id_workspace_airlock_manager': 'ab130'}

        valid_ws_1 = sample_workspace(workspace_id=str(uuid.uuid4()), auth_info=auth_info_user_in_workspace_owner_role)
        valid_ws_2 = sample_workspace(workspace_id=str(uuid.uuid4()), auth_info=auth_info_user_in_workspace_researcher_role)
        invalid_ws = sample_workspace(workspace_id=str(uuid.uuid4()), auth_info=auth_info_user_not_in_workspace_role)

        get_workspaces_mock.return_value = [valid_ws_1, valid_ws_2, invalid_ws]
        access_service_mock.return_value = [RoleAssignment('ab123', 'ab124'), RoleAssignment('ab123', 'ab126')]

        response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
        workspaces_from_response = response.json()["workspaces"]

        assert len(workspaces_from_response) == 2
        assert workspaces_from_response[0]["id"] == valid_ws_1.id
        assert workspaces_from_response[1]["id"] == valid_ws_2.id

    # [GET] /workspaces/{workspace_id}
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.get_identity_role_assignments")
    async def test_get_workspace_by_id_get_as_tre_user_returns_403(self, access_service_mock, get_workspace_mock, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'client_id': 'cl123', 'app_role_id_workspace_owner': 'ab124', 'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        access_service_mock.return_value = [RoleAssignment('ab123', 'ab124')]

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # [GET] /workspaces/{workspace_id}
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    @patch("api.routes.workspaces.get_identity_role_assignments")
    async def test_get_workspace_by_id_get_returns_404_if_resource_is_not_found(self, access_service_mock, _, app, client):
        access_service_mock.return_value = [RoleAssignment('ab123', 'ab124')]
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [GET] /workspaces/{workspace_id}/scopeid
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_get_workspaces_scope_id_returns_no_other_properties(self, _, app, client) -> None:
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SCOPE_ID_BY_WORKSPACE_ID, workspace_id=WORKSPACE_ID))
        assert response.json() == {"workspaceAuth": {"scopeId": "test_scope_id"}}

    # [GET] /workspaces/{workspace_id}/scopeid
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_get_workspaces_scope_id_returns_404_if_no_workspace_found(self, _, app, client) -> None:
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SCOPE_ID_BY_WORKSPACE_ID, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [GET] /workspaces/{workspace_id}/scopeid
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_get_workspaces_scope_id_returns_empty_if_no_scope_id(self, workspace_mock, app, client) -> None:
        no_scope_id_workspace = Workspace(
            id=WORKSPACE_ID,
            templateName="tre-workspace-base",
            templateVersion="0.1.0",
            etag="",
            properties={
                "client_id": "12345",
            },
            resourcePath=f'/workspaces/{WORKSPACE_ID}',
            updatedWhen=FAKE_CREATE_TIMESTAMP,
            user=create_admin_user()
        )

        workspace_mock.return_value = no_scope_id_workspace

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SCOPE_ID_BY_WORKSPACE_ID, workspace_id=WORKSPACE_ID))
        assert response.json() == {"workspaceAuth": {"scopeId": ""}}


class TestWorkspaceRoutesThatRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=admin_user()):
            app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin] = admin_user
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
            app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = admin_user
            app.dependency_overrides[get_current_admin_user] = admin_user
            yield
            app.dependency_overrides = {}

    # [GET] /workspaces
    @patch("api.routes.workspaces.WorkspaceRepository.get_active_workspaces")
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_workspaces_returns_correct_data_when_resources_exist(self, _, get_workspaces_mock, app, client) -> None:
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        auth_info_user_in_workspace_researcher_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab127', 'WorkspaceResearcher': 'ab126'}}
        auth_info_user_not_in_workspace_role = {'sp_id': 'ab127', 'roles': {'WorkspaceOwner': 'ab128', 'WorkspaceResearcher': 'ab129'}}

        valid_ws_1 = sample_workspace(workspace_id=str(uuid.uuid4()), auth_info=auth_info_user_in_workspace_owner_role)
        valid_ws_2 = sample_workspace(workspace_id=str(uuid.uuid4()), auth_info=auth_info_user_in_workspace_researcher_role)
        valid_ws_3 = sample_workspace(workspace_id=str(uuid.uuid4()), auth_info=auth_info_user_not_in_workspace_role)

        get_workspaces_mock.return_value = [valid_ws_1, valid_ws_2, valid_ws_3]

        response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
        workspaces_from_response = response.json()["workspaces"]

        assert len(workspaces_from_response) == 3
        assert workspaces_from_response[0]["id"] == valid_ws_1.id
        assert workspaces_from_response[1]["id"] == valid_ws_2.id
        assert workspaces_from_response[2]["id"] == valid_ws_3.id

    # [GET] /workspaces/{workspace_id}
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.get_identity_role_assignments")
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_workspace_by_id_as_tre_admin(self, _, access_service_mock, get_workspace_mock, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'client_id': 'cl123', 'app_role_id_workspace_owner': 'ab124', 'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
        workspace = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        access_service_mock.return_value = [RoleAssignment('ab123', 'ab124')]

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id=WORKSPACE_ID))
        actual_resource = response.json()["workspace"]
        assert actual_resource["id"] == workspace.id

    # [GET] /workspaces/{workspace_id}
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.get_identity_role_assignments")
    async def test_get_workspace_by_id_get_returns_422_if_workspace_id_is_not_a_uuid(self, access_service_mock, _, app, client):
        access_service_mock.return_value = [RoleAssignment('ab123', 'ab124')]
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id="not_valid"))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [GET] /workspaces/{workspace_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.get_identity_role_assignments")
    async def test_get_workspace_history_returns_workspace_history_result(self, access_service_mock, get_workspace_mock, get_resource_history_mock, app, client):
        sample_history_length = random.randint(1, 10)
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'client_id': 'cl123', 'app_role_id_workspace_owner': 'ab124', 'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
        workspace_history = sample_resource_history(history_length=sample_history_length, resource_id=WORKSPACE_ID)

        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        access_service_mock.return_value = [RoleAssignment('ab123', 'ab124')]
        get_resource_history_mock.return_value = workspace_history

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, workspace_id=WORKSPACE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == sample_history_length
        for item in obj:
            assert item["resourceId"] == WORKSPACE_ID

    # [GET] /workspaces/{workspace_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.get_identity_role_assignments")
    async def test_get_workspace_history_returns_empty_list_when_no_history(self, access_service_mock, get_workspace_mock, get_resource_history_mock, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'client_id': 'cl123', 'app_role_id_workspace_owner': 'ab124', 'app_role_id_workspace_researcher': 'ab125', 'app_role_id_workspace_airlock_manager': 'ab130'}
        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        access_service_mock.return_value = [RoleAssignment('ab123', 'ab124')]
        get_resource_history_mock.return_value = []

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, workspace_id=WORKSPACE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == 0

    # [POST] /workspaces/
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
    @patch("api.routes.workspaces.extract_auth_information")
    async def test_post_workspaces_creates_workspace(self, _, create_workspace_item, __, ___, resource_template_repo, app, client, workspace_input, basic_resource_template):
        resource_template_repo.return_value = basic_resource_template
        create_workspace_item.return_value = [sample_workspace(), basic_resource_template]
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["operation"]["resourceId"] == WORKSPACE_ID

    # [POST] /workspaces/
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
    @patch("api.routes.workspaces.WorkspaceRepository._validate_resource_parameters")
    @patch("api.routes.workspaces.extract_auth_information")
    async def test_post_workspaces_calls_db_and_service_bus(self, _, __, create_workspace_item, save_item_mock, send_resource_request_message_mock, resource_template_repo, app, client, workspace_input, basic_resource_template):
        resource_template_repo.return_value = basic_resource_template
        create_workspace_item.return_value = [sample_workspace(), basic_resource_template]
        await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        save_item_mock.assert_called_once()
        send_resource_request_message_mock.assert_called_once()

    # [POST] /workspaces/
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
    @patch("api.routes.workspaces.WorkspaceRepository._validate_resource_parameters")
    @patch("api.routes.workspaces.extract_auth_information")
    async def test_post_workspaces_returns_202_on_successful_create(self, _, __, create_workspace_item, ____, _____, resource_template_repo, app, client, workspace_input, basic_resource_template):
        resource_template_repo.return_value = basic_resource_template
        create_workspace_item.return_value = [sample_workspace(), basic_resource_template]
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["operation"]["resourceId"] == WORKSPACE_ID

    # [POST] /workspaces/
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.routes.workspaces.WorkspaceRepository.delete_item")
    @patch("api.routes.resource_helpers.send_resource_request_message", side_effect=Exception)
    @patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item", return_value=[sample_workspace(), sample_resource_template()])
    @patch("api.routes.workspaces.WorkspaceRepository._validate_resource_parameters")
    @patch("api.routes.workspaces.extract_auth_information")
    async def test_post_workspaces_returns_503_if_service_bus_call_fails(self, _, __, ___, ____, _____, delete_item_mock, resource_template_repo, app, client, workspace_input, basic_resource_template):
        resource_template_repo.return_value = basic_resource_template
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        delete_item_mock.assert_called_once_with(WORKSPACE_ID)

    # [POST] /workspaces/
    @patch("api.routes.workspaces.WorkspaceRepository.validate_input_against_template", side_effect=ValueError)
    async def test_post_workspaces_returns_400_if_template_does_not_exist(self, _, app, client, workspace_input):
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceRepository.patch_workspace", return_value=None)
    async def test_patch_workspaces_422_when_etag_not_present(self, patch_workspace_mock, get_workspace_mock, app, client):
        workspace_patch = {"isEnabled": True}

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID), json=workspace_patch)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert ("('header', 'etag')" in response.text and "field required" in response.text)

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_patch_workspaces_returns_404_if_workspace_does_not_exist(self, _, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID), json='{"isEnabled": true}', headers={"etag": "some-etag-value"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.update_item_with_etag", return_value=sample_workspace())
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.workspaces.WorkspaceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspaces_patches_workspace(self, _, __, update_item_mock, ___, ____, _____, _______, app, client):
        workspace_patch = {"isEnabled": False}
        etag = "some-etag-value"

        modified_workspace = sample_workspace()
        modified_workspace.isEnabled = False
        modified_workspace.resourceVersion = 1
        modified_workspace.user = create_admin_user()
        modified_workspace.updatedWhen = FAKE_UPDATE_TIMESTAMP

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID), json=workspace_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_workspace, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.update_item_with_etag", return_value=sample_workspace())
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.workspaces.WorkspaceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspaces_with_upgrade_major_version_returns_bad_request(self, _, __, update_item_mock, ___, ____, _____, ______, app, client):
        workspace_patch = {"templateVersion": "2.0.0"}
        etag = "some-etag-value"

        modified_workspace = sample_workspace()
        modified_workspace.isEnabled = True
        modified_workspace.resourceVersion = 1
        modified_workspace.user = create_admin_user()
        modified_workspace.updatedWhen = FAKE_UPDATE_TIMESTAMP

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID), json=workspace_patch, headers={"etag": etag})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to upgrade from 0.1.0 to 2.0.0 denied. major version upgrade is not allowed.'

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.update_item_with_etag", return_value=sample_workspace())
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspaces_with_upgrade_major_version_and_force_update_returns_patched_workspace(self, _, __, update_item_mock, ___, ____, _____, ______, app, client):
        workspace_patch = {"templateVersion": "2.0.0"}
        etag = "some-etag-value"

        modified_workspace = sample_workspace()
        modified_workspace.isEnabled = True
        modified_workspace.resourceVersion = 1
        modified_workspace.user = create_admin_user()
        modified_workspace.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_workspace.templateVersion = "2.0.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID) + "?force_version_update=True", json=workspace_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_workspace, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.update_item_with_etag", return_value=sample_workspace())
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.workspaces.WorkspaceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspaces_with_downgrade_version_returns_bad_request(self, _, __, update_item_mock, ___, ____, _____, ______, app, client):
        workspace_patch = {"templateVersion": "0.0.1"}
        etag = "some-etag-value"

        modified_workspace = sample_workspace()
        modified_workspace.isEnabled = True
        modified_workspace.resourceVersion = 1
        modified_workspace.user = create_admin_user()
        modified_workspace.updatedWhen = FAKE_UPDATE_TIMESTAMP

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID), json=workspace_patch, headers={"etag": etag})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to downgrade from 0.1.0 to 0.0.1 denied. version downgrade is not allowed.'

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.update_item_with_etag", return_value=sample_workspace())
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspaces_with_upgrade_minor_version_patches_workspace(self, _, __, update_item_mock, ___, ____, _____, ______, app, client):
        workspace_patch = {"templateVersion": "0.2.0"}
        etag = "some-etag-value"

        modified_workspace = sample_workspace()
        modified_workspace.isEnabled = True
        modified_workspace.resourceVersion = 1
        modified_workspace.user = create_admin_user()
        modified_workspace.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_workspace.templateVersion = "0.2.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID), json=workspace_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_workspace, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceRepository.update_item_with_etag", side_effect=CosmosAccessConditionFailedError)
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.workspaces.WorkspaceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspace_returns_409_if_bad_etag(self, _, __, update_item_mock, ___, ____, _____, app, client):
        workspace_patch = {"isEnabled": False}
        etag = "some-etag-value"
        modified_workspace = sample_workspace()
        modified_workspace.isEnabled = False
        modified_workspace.resourceVersion = 1
        modified_workspace.user = create_admin_user()
        modified_workspace.updatedWhen = FAKE_UPDATE_TIMESTAMP

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=WORKSPACE_ID), json=workspace_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_workspace, etag)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.ETAG_CONFLICT

    # [DELETE] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace().__dict__])
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_delete_workspace_returns_400_if_workspace_is_enabled(self, get_workspace_mock, _, app, client):
        workspace = sample_workspace()
        workspace.isEnabled = True
        get_workspace_mock.return_value = workspace

        response = await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [DELETE] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list")
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_delete_workspace_returns_400_if_associated_workspace_services_are_not_deleted(self, get_workspace_mock, resource_template_repo, resource_dependency_list_mock, disabled_workspace, app, client, basic_resource_template):
        resource_dependency_list_mock.return_value = [disabled_workspace.__dict__, sample_workspace_service().__dict__]
        get_workspace_mock.return_value = disabled_workspace
        resource_template_repo.return_value = basic_resource_template
        response = await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id=WORKSPACE_ID))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [DELETE] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list")
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.helpers.get_repository")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace", return_value=[])
    @patch('api.routes.resource_helpers.send_resource_request_message', return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    async def test_delete_workspace_sends_a_request_message_to_uninstall_the_workspace(self, send_request_message_mock, __, get_workspace_mock, get_repository_mock, resource_template_repo, ___, disabled_workspace, app, client, basic_resource_template):
        get_workspace_mock.return_value = disabled_workspace
        get_repository_mock.side_effects = [await WorkspaceRepository.create(), await WorkspaceServiceRepository.create()]
        resource_template_repo.return_value = basic_resource_template
        await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id=WORKSPACE_ID))

        send_request_message_mock.assert_called_once()

    # [DELETE] /workspaces/{workspace_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list")
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.helpers.get_repository")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace")
    async def test_delete_workspace_raises_503_if_marking_the_resource_as_deleted_in_the_db_fails(self, ___, get_workspace_mock, _____, resource_template_repo, ______, client, app, disabled_workspace, basic_resource_template):
        get_workspace_mock.return_value = disabled_workspace
        resource_template_repo.return_value = basic_resource_template
        response = await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id=WORKSPACE_ID))

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestWorkspaceServiceRoutesThatRequireOwnerRights:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_owner_user(self, app, owner_user):
        # The following ws services requires the WS app registration
        app.dependency_overrides[get_current_workspace_owner_user] = owner_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = owner_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = owner_user
        app.dependency_overrides[get_current_workspace_owner_or_airlock_manager] = owner_user
        yield
        app.dependency_overrides = {}

    # [POST] /workspaces/{workspace_id}/workspace-services
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=SERVICE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.WorkspaceServiceRepository.save_item")
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.workspaces.WorkspaceServiceRepository.create_workspace_service_item", return_value=[sample_workspace_service(), sample_resource_template()])
    async def test_post_workspace_services_creates_workspace_service(self, _, __, ___, ____, get_workspace_mock, resource_template_repo, app, client, workspace_service_input, basic_workspace_service_template):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        resource_template_repo.return_value = basic_workspace_service_template
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID), json=workspace_service_input)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["operation"]["resourceId"] == SERVICE_ID

    # [POST] /workspaces/{workspace_id}/workspace-services
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.save_and_deploy_resource", return_value=sample_resource_operation(resource_id=SERVICE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.WorkspaceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("api.routes.workspaces.WorkspaceRepository.update_item_with_etag")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_new_address_space", return_value="10.1.4.0/24")
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.workspaces.WorkspaceServiceRepository.create_workspace_service_item")
    async def test_post_workspace_services_creates_workspace_service_with_address_space(self, create_workspace_service_item_mock, __, get_workspace_mock, resource_template_repo, ___, update_item_mock, ____, _____, ______, app, client, workspace_service_input, basic_workspace_service_template, basic_resource_template):
        etag = "some-etag-value"
        workspace = sample_workspace()
        workspace.properties["address_spaces"] = ["192.168.0.1/24"]
        workspace.etag = etag
        get_workspace_mock.return_value = workspace
        basic_workspace_service_template.properties["address_space"]: str = Field()
        create_workspace_service_item_mock.return_value = [sample_workspace_service(), basic_workspace_service_template]
        basic_resource_template.properties["address_spaces"] = {"type": "array", "updateable": True}
        resource_template_repo.side_effect = [basic_resource_template, basic_workspace_service_template]

        modified_workspace = sample_workspace()
        modified_workspace.isEnabled = True
        modified_workspace.resourceVersion = 1
        modified_workspace.user = create_workspace_owner_user()
        modified_workspace.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_workspace.properties["address_spaces"] = ["192.168.0.1/24", "10.1.4.0/24"]
        modified_workspace.etag = etag
        update_item_mock.return_value = modified_workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID), json=workspace_service_input)

        update_item_mock.assert_called_once_with(modified_workspace, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["operation"]["resourceId"] == SERVICE_ID

    # [POST] /workspaces/{workspace_id}/workspace-services
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_new_address_space", return_value="10.1.4.0/24")
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=SERVICE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.workspaces.WorkspaceServiceRepository.create_workspace_service_item")
    async def test_post_workspace_services_creates_workspace_service_with_address_space_workspace_has_no_address_spaces_property(self, create_workspace_service_item_mock, __, ___, get_workspace_mock, resource_template_repo, _____, app, client, workspace_service_input, basic_workspace_service_template, basic_resource_template):
        workspace = sample_workspace()
        get_workspace_mock.return_value = workspace
        basic_workspace_service_template.properties["address_space"]: str = Field()
        create_workspace_service_item_mock.return_value = [sample_workspace_service(), basic_workspace_service_template]
        resource_template_repo.return_value = [basic_workspace_service_template, basic_resource_template]
        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID), json=workspace_service_input)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == strings.WORKSPACE_DOES_NOT_HAVE_ADDRESS_SPACES_PROPERTY

    # [POST] /workspaces/{workspace_id}/workspace-services
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=True)
    @patch("api.routes.workspaces.WorkspaceServiceRepository.create_workspace_service_item", side_effect=ValueError)
    async def test_post_workspace_services_raises_400_bad_request_if_input_is_bad(self, _, __, get_workspace_mock, app, client, workspace_service_input):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID), json=workspace_service_input)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [DELETE] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace_service().__dict__])
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_delete_workspace_service_raises_400_if_workspace_service_is_enabled(self, _, get_workspace_service_mock, __, app, client):
        workspace_service = sample_workspace_service()
        workspace_service.properties["enabled"] = True
        get_workspace_service_mock.return_value = workspace_service

        response = await client.delete(
            app.url_path_for(strings.API_DELETE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID,
                             service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [DELETE] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[disabled_workspace_service().__dict__, sample_user_resource_object().__dict__])
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id",
           return_value=disabled_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_delete_workspace_service_raises_404_if_workspace_service_has_active_resources(self,
                                                                                                 __, ___, ____, app,
                                                                                                 client):
        response = await client.delete(
            app.url_path_for(strings.API_DELETE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID,
                             service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [GET] /workspaces/{workspace_id}/services/{service_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_get_workspace_service_history_returns_workspace_service_history_result(self, get_workspace_mock, get_workspace_service_mock, get_resource_history_mock, app, client):
        sample_history_length = random.randint(1, 10)
        workspace_history = sample_resource_history(history_length=sample_history_length, resource_id=SERVICE_ID)

        get_workspace_mock.return_value = sample_workspace()
        get_workspace_service_mock.return_value = sample_workspace_service(workspace_id=WORKSPACE_ID)
        get_resource_history_mock.return_value = workspace_history

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == sample_history_length
        for item in obj:
            assert item["resourceId"] == SERVICE_ID

    # [GET] /workspaces/{workspace_id}/services/{service_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_get_workspace_service_history_returns_empty_list_when_no_history(self, get_workspace_mock, get_workspace_service_mock, get_resource_history_mock, app, client):
        get_workspace_mock.return_value = sample_workspace()
        get_workspace_service_mock.return_value = sample_workspace_service(workspace_id=WORKSPACE_ID)
        get_resource_history_mock.return_value = []

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == 0

    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[disabled_workspace_service().__dict__])
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id",
           return_value=disabled_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.UserResourceRepository.get_user_resources_for_workspace_service", return_value=[])
    @patch("api.routes.workspaces.send_uninstall_message", return_value=sample_resource_operation(resource_id=SERVICE_ID, operation_id=OPERATION_ID))
    async def test_delete_workspace_service_sends_uninstall_message(self, send_uninstall_mock, __, ___, ____, resource_template_repo, _____,
                                                                    app, client, basic_workspace_service_template):

        resource_template_repo.return_value = basic_workspace_service_template
        await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID,
                                             service_id=SERVICE_ID))
        send_uninstall_mock.assert_called_once()

    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[disabled_workspace_service().__dict__])
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.UserResourceRepository.get_user_resources_for_workspace_service", return_value=[])
    @patch("api.routes.workspaces.send_uninstall_message", return_value=sample_resource_operation(resource_id=SERVICE_ID, operation_id=OPERATION_ID))
    async def test_delete_workspace_service_returns_the_deleted_workspace_service_id(self, __, ___, ____, workspace_service_mock, resource_template_repo, _____, app, client, basic_workspace_service_template):
        workspace_service = disabled_workspace_service()
        workspace_service_mock.return_value = workspace_service
        resource_template_repo.return_value = basic_workspace_service_template
        response = await client.delete(
            app.url_path_for(strings.API_DELETE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID,
                             service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["operation"]["resourceId"] == workspace_service.id

    # GET /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.UserResourceRepository.get_user_resources_for_workspace_service")
    async def test_get_user_resources_returns_all_user_resources_for_workspace_service_if_owner(self, get_user_resources_mock, _, __, app, client):
        user_resources = [
            sample_user_resource_object(user_resource_id="a33ad738-7265-4b5f-9eae-a1a62928772a"),
            sample_user_resource_object(user_resource_id="b33ad738-7265-4b5f-9eae-a1a62928772a"),
        ]
        get_user_resources_mock.return_value = user_resources

        response = await client.get(app.url_path_for(strings.API_GET_MY_USER_RESOURCES, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["userResources"][0]["id"] == user_resources[0].id
        assert response.json()["userResources"][1]["id"] == user_resources[1].id

    # GET /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    async def test_get_user_resource_returns_a_user_resource_if_found(self, get_user_resource_mock, _, __, app, client):
        user_resource = sample_user_resource_object(user_resource_id=str(uuid.uuid4()))
        get_user_resource_mock.return_value = user_resource

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["userResource"]["id"] == user_resource.id

    # [GET] /workspaces/{workspace_id}/services/{service_id}/user-resources/{resource_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_get_user_resource_history_returns_user_resource_history_result(self, get_workspace_mock, get_workspace_service_mock, get_user_resource_mock, get_resource_history_mock, app, client):
        sample_history_length = random.randint(1, 10)
        workspace_history = sample_resource_history(history_length=sample_history_length, resource_id=USER_RESOURCE_ID)

        get_workspace_mock.return_value = sample_workspace()
        get_workspace_service_mock.return_value = sample_workspace_service()
        get_user_resource_mock.return_value = sample_user_resource_object()
        get_resource_history_mock.return_value = workspace_history

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == sample_history_length
        for item in obj:
            assert item["resourceId"] == USER_RESOURCE_ID

    # [GET] /workspaces/{workspace_id}/services/{service_id}/user-resources/{resource_id}/history
    @patch("api.routes.shared_services.ResourceHistoryRepository.get_resource_history_by_resource_id")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_get_user_resource_history_returns_empty_list_when_no_history(self, get_workspace_mock, get_workspace_service_mock, get_user_resource_mock, get_resource_history_mock, app, client):
        workspace = sample_workspace()

        get_workspace_mock.return_value = workspace
        get_workspace_service_mock.return_value = sample_workspace_service()
        get_user_resource_mock.return_value = sample_user_resource_object()
        get_resource_history_mock.return_value = []

        response = await client.get(
            app.url_path_for(strings.API_GET_RESOURCE_HISTORY, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID))

        assert response.status_code == status.HTTP_200_OK
        obj = response.json()["resource_history"]
        assert len(obj) == 0

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", side_effect=EntityDoesNotExist)
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_patch_user_resource_returns_404_if_user_resource_does_not_exist(self, _, __, ___, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json={"enabled": True})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_patch_user_resource_returns_404_if_ws_does_not_exist(self, _, __, ___, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json={"enabled": True})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @pytest.mark.parametrize('workspace_id, workspace_service_id, resource_id', [("IAmNotEvenAGUID!", SERVICE_ID, USER_RESOURCE_ID), (WORKSPACE_ID, "IAmNotEvenAGUID!", USER_RESOURCE_ID), (WORKSPACE_ID, SERVICE_ID, "IAmNotEvenAGUID")])
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_patch_user_resource_returns_422_if_invalid_id(self, get_workspace_mock, get_workspace_service_mock, get_user_resource_mock, app, client, workspace_id, workspace_service_id, resource_id):
        user_resource_to_patch = sample_user_resource_object(resource_id, workspace_id, workspace_service_id)
        get_user_resource_mock.return_value = user_resource_to_patch
        get_workspace_mock.return_value = sample_deployed_workspace(workspace_id)
        get_workspace_service_mock.return_value = sample_workspace_service(workspace_service_id, workspace_id)

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=workspace_id, service_id=workspace_service_id, resource_id=resource_id), json={"enabled": True})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.update_item_with_etag", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_user_resource_patches_user_resource(self, _, update_item_mock, __, ___, ____, _____, ______, _______, ________, app, client):
        user_resource_service_patch = {"isEnabled": False}
        etag = "some-etag-value"

        modified_user_resource = sample_user_resource_object()
        modified_user_resource.isEnabled = False
        modified_user_resource.resourceVersion = 1
        modified_user_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_user_resource.user = create_workspace_owner_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_service_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_user_resource, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.update_item_with_etag", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("db.repositories.resources.ResourceRepository.create", return_value=AsyncMock())
    async def test_patch_user_resource_with_upgrade_major_version_returns_bad_request(self, _, __, ___, ____, _____, ______, _______, ________, _________, __________, app, client):
        user_resource_service_patch = {"templateVersion": "2.0.0"}
        etag = "some-etag-value"

        modified_user_resource = sample_user_resource_object()
        modified_user_resource.isEnabled = True
        modified_user_resource.resourceVersion = 1
        modified_user_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_user_resource.user = create_workspace_owner_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_service_patch, headers={"etag": etag})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to upgrade from 0.1.0 to 2.0.0 denied. major version upgrade is not allowed.'

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.update_item_with_etag", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("db.repositories.resources.ResourceRepository.create", return_value=AsyncMock())
    @patch("db.repositories.resources.ResourceRepository.get_resource_by_id", return_value=AsyncMock())
    async def test_patch_user_resource_with_upgrade_major_version_and_force_update_returns_patched_user_resource(self, _, __, ___, update_item_mock, ____, _____, ______, _______, ________, _________, resource_history_repo_save_item_mock, app, client):
        user_resource_service_patch = {"templateVersion": "2.0.0"}
        etag = "some-etag-value"

        modified_user_resource = sample_user_resource_object()
        modified_user_resource.isEnabled = True
        modified_user_resource.resourceVersion = 1
        modified_user_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_user_resource.user = create_workspace_owner_user()
        modified_user_resource.templateVersion = "2.0.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID) + "?force_version_update=True", json=user_resource_service_patch, headers={"etag": etag})
        resource_history_repo_save_item_mock.assert_called_once()
        update_item_mock.assert_called_once_with(modified_user_resource, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.OperationRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.update_item_with_etag", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("db.repositories.resources.ResourceRepository.create", return_value=AsyncMock())
    async def test_patch_user_resource_with_downgrade_version_returns_bad_request(self, _, __, ___, ____, _____, ______, _______, ________, _________, __________, ___________, app, client):
        user_resource_service_patch = {"templateVersion": "0.0.1"}
        etag = "some-etag-value"

        modified_user_resource = sample_user_resource_object()
        modified_user_resource.isEnabled = True
        modified_user_resource.resourceVersion = 1
        modified_user_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_user_resource.user = create_workspace_owner_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_service_patch, headers={"etag": etag})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to downgrade from 0.1.0 to 0.0.1 denied. version downgrade is not allowed.'

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.update_item_with_etag", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("db.repositories.resources.ResourceRepository.create", return_value=AsyncMock())
    @patch("db.repositories.resources.ResourceRepository.get_resource_by_id", return_value=AsyncMock())
    async def test_patch_user_resource_with_upgrade_minor_version_patches_user_resource(self, __, ___, ____, update_item_mock, _____, ______, _______, ________, _________, __________, ___________, app, client):
        user_resource_service_patch = {"templateVersion": "0.2.0"}
        etag = "some-etag-value"

        modified_user_resource = sample_user_resource_object()
        modified_user_resource.isEnabled = True
        modified_user_resource.resourceVersion = 1
        modified_user_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_user_resource.user = create_workspace_owner_user()
        modified_user_resource.templateVersion = "0.2.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_service_patch, headers={"etag": etag})
        update_item_mock.assert_called_once_with(modified_user_resource, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.update_item_with_etag", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    @patch("db.repositories.resources.ResourceRepository.create", return_value=AsyncMock())
    @patch("db.repositories.resources.ResourceRepository.get_resource_by_id", return_value=AsyncMock())
    async def test_patch_user_resource_validates_against_template(self, _, __, ___, update_item_mock, ____, _____, ______, _______, ________, _________, __________, app, client):
        user_resource_service_patch = {'isEnabled': False, 'properties': {'vm_size': 'large'}}
        etag = "some-etag-value"

        modified_resource = sample_user_resource_object()
        modified_resource.isEnabled = False
        modified_resource.resourceVersion = 1
        modified_resource.properties["vm_size"] = "large"
        modified_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_resource.user = create_workspace_owner_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_service_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_resource, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_user_resource_400_when_invalid(self, _, __, ___, ____, _____, ______, app, client):
        user_resource_service_patch = {'isEnabled': False, 'properties': {'vm_size': 'INVALID-DATA'}}
        etag = "some-etag-value"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_service_patch, headers={"etag": etag})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", side_effect=EntityDoesNotExist)
    async def test_patch_workspace_service_returns_404_if_workspace_service_does_not_exist(self, _, __, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json='{"enabled": true}')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_patch_workspace_service_returns_404_if_workspace_does_not_exist(self, _, __, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json='{"enabled": true}')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceServiceRepository.patch_workspace_service", side_effect=CosmosAccessConditionFailedError)
    async def test_patch_workspace_service_returns_409_if_bad_etag(self, _, __, ___, app, client):
        workspace_service_patch = {"isEnabled": True}
        etag = "some-bad-etag-value"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=workspace_service_patch, headers={"etag": etag})
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.ETAG_CONFLICT

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @pytest.mark.parametrize('workspace_id, workspace_service_id', [("933ad738-7265-4b5f-9eae-a1a62928772e", "IAmNotEvenAGUID!"), ("IAmNotEvenAGUID!", "933ad738-7265-4b5f-9eae-a1a62928772e")])
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_patch_workspace_service_returns_422_if_invalid_id(self, get_workspace_mock, get_workspace_service_mock, app, client, workspace_id, workspace_service_id):
        workspace_service_to_patch = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service_to_patch
        get_workspace_mock.return_value = sample_deployed_workspace(workspace_id)

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=workspace_id, service_id=workspace_service_id), json={"enabled": True})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace_service().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceServiceRepository.update_item_with_etag", return_value=sample_workspace_service())
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspace_service_patches_workspace_service(self, _, update_item_mock, get_workspace_mock, __, ___, ____, _____, ______, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}

        get_workspace_mock.return_value = sample_deployed_workspace(WORKSPACE_ID, auth_info_user_in_workspace_owner_role)
        etag = "some-etag-value"
        workspace_service_patch = {"isEnabled": False}

        modified_workspace_service = sample_workspace_service()
        modified_workspace_service.isEnabled = False
        modified_workspace_service.resourceVersion = 1
        modified_workspace_service.user = create_workspace_owner_user()
        modified_workspace_service.updatedWhen = FAKE_UPDATE_TIMESTAMP

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=workspace_service_patch, headers={"etag": etag})
        update_item_mock.assert_called_once_with(modified_workspace_service, etag)

        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace_service().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceServiceRepository.update_item_with_etag", return_value=sample_workspace_service())
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspace_service_with_upgrade_major_version_returns_bad_request(self, _, update_item_mock, get_workspace_mock, __, ___, ____, _____, ______, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}

        get_workspace_mock.return_value = sample_deployed_workspace(WORKSPACE_ID, auth_info_user_in_workspace_owner_role)
        etag = "some-etag-value"
        workspace_service_patch = {"templateVersion": "2.0.0"}

        modified_workspace_service = sample_workspace_service()
        modified_workspace_service.isEnabled = True
        modified_workspace_service.resourceVersion = 1
        modified_workspace_service.user = create_workspace_owner_user()
        modified_workspace_service.updatedWhen = FAKE_UPDATE_TIMESTAMP

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=workspace_service_patch, headers={"etag": etag})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to upgrade from 0.1.0 to 2.0.0 denied. major version upgrade is not allowed.'

    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace_service().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceServiceRepository.update_item_with_etag", return_value=sample_workspace_service())
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspace_service_with_upgrade_major_version_and_force_update_returns_patched_workspace_service(self, _, update_item_mock, get_workspace_mock, __, ___, ____, _____, ______, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}

        get_workspace_mock.return_value = sample_deployed_workspace(WORKSPACE_ID, auth_info_user_in_workspace_owner_role)
        etag = "some-etag-value"
        workspace_service_patch = {"templateVersion": "2.0.0"}

        modified_workspace_service = sample_workspace_service()
        modified_workspace_service.isEnabled = True
        modified_workspace_service.resourceVersion = 1
        modified_workspace_service.user = create_workspace_owner_user()
        modified_workspace_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_workspace_service.templateVersion = "2.0.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID) + "?force_version_update=True", json=workspace_service_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_workspace_service, etag)
        assert response.status_code == status.HTTP_202_ACCEPTED

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace_service().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceServiceRepository.update_item_with_etag", return_value=sample_workspace_service())
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspace_service_with_downgrade_version_returns_bad_request(self, _, update_item_mock, get_workspace_mock, __, ___, ____, _____, ______, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}

        get_workspace_mock.return_value = sample_deployed_workspace(WORKSPACE_ID, auth_info_user_in_workspace_owner_role)
        etag = "some-etag-value"
        workspace_service_patch = {"templateVersion": "0.0.1"}

        modified_workspace_service = sample_workspace_service()
        modified_workspace_service.isEnabled = True
        modified_workspace_service.resourceVersion = 1
        modified_workspace_service.user = create_workspace_owner_user()
        modified_workspace_service.updatedWhen = FAKE_UPDATE_TIMESTAMP

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=workspace_service_patch, headers={"etag": etag})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.text == 'Attempt to downgrade from 0.1.0 to 0.0.1 denied. version downgrade is not allowed.'

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @patch("api.routes.resource_helpers.ResourceRepository.get_resource_dependency_list", return_value=[sample_workspace_service().__dict__])
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.workspaces.send_resource_request_message", return_value=sample_resource_operation(resource_id=WORKSPACE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=sample_resource_template())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.WorkspaceServiceRepository.update_item_with_etag", return_value=sample_workspace_service())
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_workspace_service_with_upgrade_minor_version_patches_workspace(self, _, update_item_mock, get_workspace_mock, __, ___, ____, _____, ______, app, client):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}

        get_workspace_mock.return_value = sample_deployed_workspace(WORKSPACE_ID, auth_info_user_in_workspace_owner_role)
        etag = "some-etag-value"
        workspace_service_patch = {"templateVersion": "0.2.0"}

        modified_workspace_service = sample_workspace_service()
        modified_workspace_service.isEnabled = True
        modified_workspace_service.resourceVersion = 1
        modified_workspace_service.user = create_workspace_owner_user()
        modified_workspace_service.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_workspace_service.templateVersion = "0.2.0"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=workspace_service_patch, headers={"etag": etag})
        update_item_mock.assert_called_once_with(modified_workspace_service, etag)

        assert response.status_code == status.HTTP_202_ACCEPTED


class TestWorkspaceServiceRoutesThatRequireOwnerOrResearcherRights:
    @pytest.fixture(autouse=True, scope='class')
    def log_in_with_researcher_user(self, app, researcher_user):
        # The following ws services requires the WS app registration
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = researcher_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user] = researcher_user
        app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin] = researcher_user
        yield
        app.dependency_overrides = {}

    # [GET] /workspaces/{workspace_id}
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_get_workspace_by_id_get_as_workspace_researcher(self, _, __, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_200_OK

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_templates_information", return_value=[ResourceTemplateInformation(name="test")])
    async def test_get_workspace_service_templates_returns_templates(self, _, __, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_TEMPLATES_IN_WORKSPACE, workspace_id=WORKSPACE_ID))
        assert response.status_code == status.HTTP_200_OK

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_templates_information", return_value=[ResourceTemplateInformation(name="test")])
    async def test_get_user_resource_templates_returns_templates(self, _, __, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE_TEMPLATES_IN_WORKSPACE, workspace_id=WORKSPACE_ID, service_template_name="guacamole"))
        assert response.status_code == status.HTTP_200_OK

    # [GET] /workspaces/{workspace_id}/workspace-services
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace",
           return_value=None)
    async def test_get_workspace_services_returns_workspace_services_for_workspace(self,
                                                                                   get_active_workspace_services_mock,
                                                                                   _, __, app, client):
        workspace_services = [sample_workspace_service()]
        get_active_workspace_services_mock.return_value = workspace_services

        response = await client.get(
            app.url_path_for(strings.API_GET_ALL_WORKSPACE_SERVICES, workspace_id=WORKSPACE_ID))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["workspaceServices"][0]["id"] == sample_workspace_service().id

    # [GET] /workspaces/{workspace_id}/workspace-services/{service_id}
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_get_workspace_service_raises_404_if_associated_workspace_is_not_found(self, _,
                                                                                         get_workspace_service_mock,
                                                                                         app, client):
        get_workspace_service_mock.return_value = sample_workspace_service(SERVICE_ID, WORKSPACE_ID)

        response = await client.get(
            app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_BY_ID, workspace_id=WORKSPACE_ID,
                             service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [GET] /workspaces/{workspace_id}/workspace-services/{service_id}
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    async def test_get_workspace_service_returns_workspace_service_result(self, _, __, get_workspace_service_mock,
                                                                          app, client):
        workspace_service = sample_workspace_service(workspace_service_id=str(uuid.uuid4()))
        get_workspace_service_mock.return_value = workspace_service

        response = await client.get(
            app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_BY_ID, workspace_id=WORKSPACE_ID,
                             service_id=SERVICE_ID))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["workspaceService"]["id"] == workspace_service.id

    # [GET] /workspaces/{workspace_id}/workspace-services/{service_id}
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id",
           side_effect=EntityDoesNotExist)
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=None)
    async def test_get_workspace_service_raises_404_if_workspace_service_is_not_found(self, _, __, app, client):
        response = await client.get(
            app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_BY_ID, workspace_id=WORKSPACE_ID,
                             service_id=SERVICE_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("api.routes.workspaces.enrich_resource_with_available_upgrades", return_value=None)
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.UserResourceRepository.get_user_resources_for_workspace_service")
    async def test_get_user_resources_returns_own_user_resources_for_researcher(self, get_user_resources_mock_awaited_mock, _, __, app, client, non_admin_user):
        not_my_user_id = "def"
        my_user_id = non_admin_user().id

        my_user_resource1 = sample_user_resource_object(user_resource_id="a33ad738-7265-4b5f-9eae-a1a62928772a")
        my_user_resource1.ownerId = my_user_id
        my_user_resource2 = sample_user_resource_object(user_resource_id="b33ad738-7265-4b5f-9eae-a1a62928772a")
        my_user_resource2.ownerId = my_user_id
        not_my_user_resource = sample_user_resource_object(user_resource_id="c33ad738-7265-4b5f-9eae-a1a62928772a")
        not_my_user_resource.ownerId = not_my_user_id
        get_user_resources_mock_awaited_mock.return_value = [my_user_resource1, my_user_resource2, not_my_user_resource]

        response = await client.get(app.url_path_for(strings.API_GET_MY_USER_RESOURCES, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID))
        assert response.status_code == status.HTTP_200_OK
        actual_returned_resources = response.json()["userResources"]
        assert len(actual_returned_resources) == 2
        assert actual_returned_resources[0]["id"] == my_user_resource1.id
        assert actual_returned_resources[1]["id"] == my_user_resource2.id

    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", side_effect=EntityDoesNotExist)
    async def test_get_user_resource_raises_404_if_resource_not_found(self, _, __, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id")
    @patch("api.routes.workspaces.UserResourceRepository.create_user_resource_item", side_effect=ValueError)
    async def test_post_user_resources_raises_400_bad_request_if_input_is_bad(self, _, __, get_workspace_mock, app, client, sample_user_resource_input_data):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.UserResourceRepository.save_item")
    @patch("api.routes.workspaces.UserResourceRepository.create_user_resource_item")
    async def test_post_user_resources_creates_user_resource(self, create_user_resource_item_mock, _, __, ___, get_workspace_mock, resource_template_repo, app, client, sample_user_resource_input_data, basic_user_resource_template):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        resource_template_repo.return_value = basic_user_resource_template
        create_user_resource_item_mock.return_value = [sample_user_resource_object(), sample_resource_template()]

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["operation"]["resourceId"] == USER_RESOURCE_ID

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.UserResourceRepository.save_item")
    @patch("api.routes.workspaces.UserResourceRepository.create_user_resource_item")
    async def test_post_user_resources_creates_user_resource_and_assigns_another_user(self, create_user_resource_item_mock, _, __, ___, get_workspace_mock, resource_template_repo, app, client, sample_user_resource_input_data, basic_user_resource_template):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        resource_template_repo.return_value = basic_user_resource_template

        # Create a sample_user_resource_object but change the properties.owner_id value
        sample_user_resource_input_data_with_owner_id = sample_user_resource_input_data
        sample_user_resource_input_data_with_owner_id["properties"]["assign_to_another_user"] = True
        sample_user_resource_input_data_with_owner_id["properties"]["owner_id"] = "ab126"

        create_user_resource_item_mock.return_value = [sample_user_resource_object(), sample_resource_template()]

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data_with_owner_id)

        assert response.status_code == status.HTTP_202_ACCEPTED

        # Check the mock was called with owner_id="ab126"
        called_args = create_user_resource_item_mock.call_args.args
        assert called_args[6] == "ab126"
        assert response.json()["operation"]["resourceId"] == USER_RESOURCE_ID

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id")
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.UserResourceRepository.save_item")
    async def test_post_user_resources_returns_400_when_no_ownerid_passed(self, _, __, ___, get_workspace_mock, resource_template_repo, app, client, sample_user_resource_input_data, basic_user_resource_template):
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        get_workspace_mock.return_value = sample_workspace(auth_info=auth_info_user_in_workspace_owner_role)
        resource_template_repo.return_value = basic_user_resource_template

        # Create a sample_user_resource_object but change the properties.owner_id value
        sample_user_resource_input_data_with_assign_to_another_user = sample_user_resource_input_data
        sample_user_resource_input_data_with_assign_to_another_user["properties"]["assign_to_another_user"] = True
        # Don't set the owner_id in the input data

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data_with_assign_to_another_user)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_post_user_resources_with_non_existing_workspace_id_returns_404(self, _, app, client, sample_user_resource_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id", side_effect=EntityDoesNotExist)
    async def test_post_user_resources_with_non_existing_service_id_returns_404(self, _, __, app, client, sample_user_resource_input_data):
        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=False)
    @patch("api.routes.workspaces.OperationRepository.create_operation_item")
    async def test_post_user_resources_with_non_deployed_workspace_id_returns_404(self, get_deployed_workspace_by_workspace_id_mock, _, __, app, client, sample_user_resource_input_data):
        workspace = sample_workspace()
        get_deployed_workspace_by_workspace_id_mock.return_value = workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.WORKSPACE_IS_NOT_DEPLOYED

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_id")  # skip the deployment check on this one and return a happy workspace (mock)
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")  # mock the workspace_service item, but still call the resource_has_deployed_operation
    @patch("api.routes.workspaces.OperationRepository.resource_has_deployed_operation", return_value=False)  # only called for the service, not the workspace
    async def test_post_user_resources_with_non_deployed_service_id_returns_404(self, _, get_workspace_service_mock, get_deployed_workspace_mock, app, client, sample_user_resource_input_data):
        workspace = sample_workspace()
        get_deployed_workspace_mock.return_value = workspace

        workspace_service = sample_workspace_service()
        get_workspace_service_mock.return_value = workspace_service

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID), json=sample_user_resource_input_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.WORKSPACE_SERVICE_IS_NOT_DEPLOYED

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.patch_user_resource", side_effect=CosmosAccessConditionFailedError)
    async def test_patch_user_resource_returns_409_if_bad_etag(self, _, __, ___, ____, _____, app, client):
        user_resource_patch = {"isEnabled": True}
        etag = "some-bad-etag-value"

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_patch, headers={"etag": etag})
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.ETAG_CONFLICT

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", side_effect=EntityDoesNotExist)
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_patch_user_resource_returns_404_if_user_resource_does_not_exist(self, _, __, ___, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json={"enabled": True})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", side_effect=EntityDoesNotExist)
    async def test_patch_user_resource_returns_404_if_ws_does_not_exist(self, _, __, ___, app, client):
        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json={"enabled": True})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @pytest.mark.parametrize('workspace_id, workspace_service_id, resource_id', [("IAmNotEvenAGUID!", SERVICE_ID, USER_RESOURCE_ID), (WORKSPACE_ID, "IAmNotEvenAGUID!", USER_RESOURCE_ID), (WORKSPACE_ID, SERVICE_ID, "IAmNotEvenAGUID")])
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    async def test_patch_user_resource_returns_422_if_invalid_id(self, get_workspace_mock, get_workspace_service_mock, get_user_resource_mock, app, client, workspace_id, workspace_service_id, resource_id):
        user_resource_to_patch = sample_user_resource_object(resource_id, workspace_id, workspace_service_id)
        get_user_resource_mock.return_value = user_resource_to_patch
        get_workspace_mock.return_value = sample_deployed_workspace(workspace_id)
        get_workspace_service_mock.return_value = sample_workspace_service(workspace_service_id, workspace_id)

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=workspace_id, service_id=workspace_service_id, resource_id=resource_id), json={"enabled": True})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [PATCH] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources/{resource_id}
    @patch("api.routes.workspaces.ResourceHistoryRepository.save_item", return_value=AsyncMock())
    @patch("api.routes.resource_helpers.send_resource_request_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version", return_value=None)
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", return_value=sample_workspace_service())
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.update_item_with_etag", return_value=sample_user_resource_object())
    @patch("api.routes.workspaces.UserResourceRepository.get_timestamp", return_value=FAKE_UPDATE_TIMESTAMP)
    async def test_patch_user_resources_patches_user_resource(self, _, update_item_mock, __, ___, ____, _____, ______, _______, ________, app, client):
        user_resource_service_patch = {"isEnabled": False}
        etag = "some-etag-value"

        modified_user_resource = sample_user_resource_object()
        modified_user_resource.isEnabled = False
        modified_user_resource.resourceVersion = 1
        modified_user_resource.updatedWhen = FAKE_UPDATE_TIMESTAMP
        modified_user_resource.user = create_workspace_researcher_user()

        response = await client.patch(app.url_path_for(strings.API_UPDATE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID), json=user_resource_service_patch, headers={"etag": etag})

        update_item_mock.assert_called_once_with(modified_user_resource, etag)

        assert response.status_code == status.HTTP_202_ACCEPTED

    # [DELETE] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    async def test_delete_user_resource_raises_400_if_user_resource_is_enabled(self, _, get_user_resource_mock, ___, ____, resource_template_repo, app, client, basic_user_resource_template):
        user_resource = sample_user_resource_object()
        get_user_resource_mock.return_value = user_resource

        resource_template_repo.return_value = basic_user_resource_template

        response = await client.delete(app.url_path_for(strings.API_DELETE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", return_value=disabled_user_resource())
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.routes.workspaces.send_uninstall_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    async def test_delete_user_resource_sends_uninstall_message(self, send_uninstall_mock, __, ___, ____, _____, resource_template_repo, app, client, basic_user_resource_template):
        resource_template_repo.return_value = basic_user_resource_template
        await client.delete(app.url_path_for(strings.API_DELETE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID))
        send_uninstall_mock.assert_called_once()

    @patch("api.routes.workspaces.ResourceTemplateRepository.get_template_by_name_and_version")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id")
    @patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    @patch("api.routes.workspaces.validate_user_has_valid_role_for_user_resource")
    @patch("api.routes.workspaces.send_uninstall_message", return_value=sample_resource_operation(resource_id=USER_RESOURCE_ID, operation_id=OPERATION_ID))
    async def test_delete_user_resource_returns_resource_id(self, __, ___, get_user_resource_mock, ____, _____, resource_template_repo, app, client, basic_user_resource_template):
        user_resource = disabled_user_resource()
        get_user_resource_mock.return_value = user_resource
        resource_template_repo.return_value = basic_user_resource_template

        response = await client.delete(app.url_path_for(strings.API_DELETE_USER_RESOURCE, workspace_id=WORKSPACE_ID, service_id=SERVICE_ID, resource_id=USER_RESOURCE_ID))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["operation"]["resourceId"] == user_resource.id
