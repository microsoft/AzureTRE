import uuid
import pytest
from mock import patch, MagicMock

from fastapi import HTTPException
from starlette import status

from api.routes.workspaces import get_current_user, save_and_deploy_resource, validate_user_is_owner_or_researcher_in_workspace
from db.errors import EntityDoesNotExist
from db.repositories.resources import ResourceRepository
from db.repositories.workspaces import WorkspaceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from models.domain.resource import Status, Deployment, RequestAction
from models.domain.user_resource import UserResource
from models.domain.workspace import Workspace, WorkspaceRole
from models.domain.workspace_service import WorkspaceService
from resources import strings


pytestmark = pytest.mark.asyncio


def sample_workspace(workspace_id, auth_info: dict = None):
    workspace = Workspace(
        id=workspace_id,
        resourceTemplateName="tre-workspace-base",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
    )
    if auth_info:
        workspace.authInformation = auth_info
    return workspace


def sample_deployed_workspace(workspace_id, auth_info: dict = None):
    workspace = Workspace(
        id=workspace_id,
        resourceTemplateName="tre-workspace-base",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.Deployed, message=""),
    )
    if auth_info:
        workspace.authInformation = auth_info
    return workspace


def sample_workspace_service(workspace_service_id, workspace_id):
    return WorkspaceService(
        id=workspace_service_id,
        workspaceId=workspace_id,
        resourceTemplateName="tre-workspace-base",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
    )


@pytest.fixture
def resource_repo() -> ResourceRepository:
    with patch("azure.cosmos.CosmosClient") as cosmos_client_mock:
        return ResourceRepository(cosmos_client_mock)


@pytest.fixture
def workspace_service_input():
    return {
        "workspaceServiceType": "test-workspace-service",
        "properties": {
            "display_name": "display",
            "app_id": "f0acf127-a672-a672-a672-a15e5bf9f127"
        }
    }


def sample_user_resource_object(user_resource_id, workspace_id, parent_workspace_service_id):
    user_resource = UserResource(
        id=user_resource_id,
        workspaceId=workspace_id,
        parentWorkspaceServiceId=parent_workspace_service_id,
        resourceTemplateName="tre-user-resource",
        resourceTemplateVersion="0.1.0",
        resourceTemplateParameters={},
        deployment=Deployment(status=Status.NotDeployed, message=""),
    )

    return user_resource


@pytest.fixture
def sample_user_resource_input_data():
    return {
        "userResourceType": "test-user-resource",
        "properties": {
            "display_name": "display",
            "app_id": "f0acf127-a672-a672-a672-a15e5bf9f127"
        }
    }


@pytest.fixture
def workspace_input():
    return {
        "workspaceType": "test-workspace",
        "properties": {
            "display_name": "display",
            "app_id": "f0acf127-a672-a672-a672-a15e5bf9f127"
        }
    }


@pytest.fixture
def disabled_workspace() -> Workspace:
    workspace = sample_workspace("abc")
    workspace.resourceTemplateParameters["enabled"] = False
    return workspace


# Test helpers
@patch("api.routes.workspaces.send_resource_request_message", return_value=None)
async def test_save_and_deploy_resource_saves_item(_, resource_repo):
    resource = sample_workspace(str(uuid.uuid4()))
    resource_repo.save_item = MagicMock(return_value=None)

    await save_and_deploy_resource(resource, resource_repo)

    resource_repo.save_item.assert_called_once_with(resource)


async def test_save_and_deploy_resource_raises_503_if_save_to_db_fails(resource_repo):
    resource = sample_workspace(str(uuid.uuid4()))
    resource_repo.save_item = MagicMock(side_effect=Exception)

    with pytest.raises(HTTPException) as ex:
        await save_and_deploy_resource(resource, resource_repo)
    assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@patch("api.routes.workspaces.send_resource_request_message", return_value=None)
async def test_save_and_deploy_resource_sends_resource_request_message(send_resource_request_mock, resource_repo):
    resource = sample_workspace(str(uuid.uuid4()))
    resource_repo.save_item = MagicMock(return_value=None)

    await save_and_deploy_resource(resource, resource_repo)

    send_resource_request_mock.assert_called_once_with(resource, RequestAction.Install)


@patch("api.routes.workspaces.send_resource_request_message")
async def test_save_and_deploy_resource_raises_503_if_send_request_fails(send_resource_request_mock, resource_repo):
    resource = sample_workspace(str(uuid.uuid4()))
    resource_repo.save_item = MagicMock(return_value=None)
    resource_repo.delete_item = MagicMock(return_value=None)
    send_resource_request_mock.side_effect = Exception

    with pytest.raises(HTTPException) as ex:
        await save_and_deploy_resource(resource, resource_repo)
    assert ex.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@patch("api.routes.workspaces.send_resource_request_message")
async def test_save_and_deploy_resource_deletes_item_from_db_if_send_request_fails(send_resource_request_mock, resource_repo):
    resource = sample_workspace(str(uuid.uuid4()))
    resource_repo.save_item = MagicMock(return_value=None)
    resource_repo.delete_item = MagicMock(return_value=None)
    send_resource_request_mock.side_effect = Exception

    with pytest.raises(HTTPException):
        await save_and_deploy_resource(resource, resource_repo)

    resource_repo.delete_item.assert_called_once_with(resource.id)


@patch("api.routes.workspaces.get_access_service")
async def test_validate_user_is_owner_or_researcher_raises_403_if_user_is_not_owner_or_researcher(get_access_service_mock, non_admin_user):
    from services.authentication import AADAccessService
    from models.domain.workspace import WorkspaceRole

    access_service = AADAccessService()
    get_access_service_mock.return_value = access_service
    access_service.get_workspace_role = MagicMock(return_value=WorkspaceRole.NoRole)
    workspace = sample_workspace(str(uuid.uuid4()))
    user = non_admin_user

    with pytest.raises(HTTPException) as ex:
        validate_user_is_owner_or_researcher_in_workspace(user, workspace)

    assert ex.value.status_code == status.HTTP_403_FORBIDDEN
    access_service.get_workspace_role.assert_called_once_with(user, workspace)


class TestWorkspaceRoutesThatDontRequireAdminRights:
    # [GET] /workspaces
    @ patch("api.routes.workspaces.WorkspaceRepository.get_active_workspaces")
    async def test_workspaces_get_empty_list_when_no_resources_exist(self, get_workspaces_mock, app, client) -> None:
        get_workspaces_mock.return_value = []

        response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
        assert response.json() == {"workspaces": []}

    # [GET] /workspaces
    @ patch("api.routes.workspaces.WorkspaceRepository.get_active_workspaces")
    async def test_workspaces_get_list_returns_correct_data_when_resources_exist(self, get_workspaces_mock, app, client) -> None:
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        auth_info_user_in_workspace_researcher_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab127', 'WorkspaceResearcher': 'ab124'}}
        auth_info_user_not_in_workspace_role = {'sp_id': 'ab127', 'roles': {'WorkspaceOwner': 'ab128', 'WorkspaceResearcher': 'ab129'}}

        valid_ws_1 = sample_workspace("2fdc9fba-726e-4db6-a1b8-9018a2165748", auth_info_user_in_workspace_owner_role)
        valid_ws_2 = sample_workspace("000000d3-82da-4bfc-b6e9-9a7853ef753e", auth_info_user_in_workspace_researcher_role)
        invalid_ws = sample_workspace("00000045-82da-4bfc-b6e9-9a7853ef7534", auth_info_user_not_in_workspace_role)

        get_workspaces_mock.return_value = [valid_ws_1, valid_ws_2, invalid_ws]

        response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACES))
        workspaces_from_response = response.json()["workspaces"]

        assert len(workspaces_from_response) == 2
        assert valid_ws_1 in workspaces_from_response
        assert valid_ws_2 in workspaces_from_response

    # [GET] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspaces_id_get_returns_404_if_resource_is_not_found(self, get_workspace_mock, app, client):
        get_workspace_mock.side_effect = EntityDoesNotExist

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id="000000d3-82da-4bfc-b6e9-9a7853ef753e"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [GET] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspaces_id_get_returns_422_if_workspace_id_is_not_a_uuid(self, get_workspace_mock, app, client):
        get_workspace_mock.side_effect = EntityDoesNotExist

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id="not_valid"))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [GET] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspaces_id_get_returns_workspace_if_found(self, get_workspace_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(workspace_id, auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_BY_ID, workspace_id=workspace_id))
        actual_resource = response.json()["workspace"]
        assert actual_resource["id"] == workspace.id

    # [GET] /workspaces/{workspace_id}/workspace-services
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.validate_user_is_owner_or_researcher_in_workspace", return_value=None)
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace")
    async def test_get_workspace_services_validates_user_is_owner_or_researcher(self, get_active_workspace_services_mock, validate_user_mock, get_workspace_by_id_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        get_workspace_by_id_mock.return_value = sample_workspace(workspace_id)
        get_active_workspace_services_mock.return_value = []

        await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACE_SERVICES, workspace_id=workspace_id))

        validate_user_mock.assert_called_once()

    # [GET] /workspaces/{workspace_id}/workspace-services
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.validate_user_is_owner_or_researcher_in_workspace", return_value=None)
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace", return_value=None)
    async def test_get_workspace_services_returns_workspace_services_for_workspace(self, get_active_workspace_services_mock, _, get_workspace_by_id_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"
        get_workspace_by_id_mock.return_value = sample_workspace(workspace_id)
        workspace_services = [sample_workspace_service(workspace_service_id, workspace_id)]
        get_active_workspace_services_mock.return_value = workspace_services

        response = await client.get(app.url_path_for(strings.API_GET_ALL_WORKSPACE_SERVICES, workspace_id=workspace_id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["workspaceServices"] == workspace_services

    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.routes.workspaces.get_workspace_by_id")
    @ patch("api.routes.workspaces.validate_user_is_owner_or_researcher_in_workspace", return_value=None)
    async def test_get_workspace_service_returns_workspace_service_result(self, _, get_workspace_mock, get_workspace_service_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"
        get_workspace_mock.return_value = sample_workspace(workspace_id)
        workspace_service = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_BY_ID, service_id=workspace_service_id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["workspaceService"] == workspace_service

    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.routes.workspaces.get_workspace_by_id")
    @ patch("api.routes.workspaces.validate_user_is_owner_or_researcher_in_workspace", return_value=None)
    async def test_get_workspace_service_validates_that_user_is_owner_or_researcher_in_workspace(self, validate_user_mock, get_workspace_mock, get_workspace_service_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"
        get_workspace_mock.return_value = sample_workspace(workspace_id)
        workspace_service = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service

        await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_BY_ID, service_id=workspace_service_id))

        validate_user_mock.assert_called_once()

    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id", side_effect=EntityDoesNotExist)
    async def test_get_workspace_service_raises_404_if_workspace_service_is_not_found(self, _, app, client):
        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_BY_ID, service_id="abcad738-7265-4b5f-9eae-a1a62928772e"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id", side_effect=EntityDoesNotExist)
    async def test_get_workspace_service_raises_404_if_associated_workspace_is_not_found(self, _, get_workspace_service_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"
        get_workspace_service_mock.return_value = sample_workspace_service(workspace_service_id, workspace_id)

        response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_SERVICE_BY_ID, service_id=workspace_service_id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @ patch("api.routes.workspaces.UserResourceRepository.get_user_resources_for_workspace_service")
    @ patch("api.routes.workspaces.get_workspace_by_id", return_value=None)
    @ patch("api.routes.workspaces.get_user_role_in_workspace", return_value=WorkspaceRole.Owner)
    async def test_get_user_resources_returns_all_user_resources_for_workspace_service_if_owner(self, _, __, get_user_resources_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"
        user_resources = [
            sample_user_resource_object(user_resource_id="a33ad738-7265-4b5f-9eae-a1a62928772a", workspace_id=workspace_id, parent_workspace_service_id=workspace_service_id),
            sample_user_resource_object(user_resource_id="b33ad738-7265-4b5f-9eae-a1a62928772a", workspace_id=workspace_id, parent_workspace_service_id=workspace_service_id),
        ]
        get_user_resources_mock.return_value = user_resources

        response = await client.get(app.url_path_for(strings.API_GET_MY_USER_RESOURCES, service_id=workspace_service_id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["userResources"] == user_resources

    @ patch("api.routes.workspaces.UserResourceRepository.get_user_resources_for_workspace_service")
    @ patch("api.routes.workspaces.get_workspace_by_id", return_value=None)
    @ patch("api.routes.workspaces.get_user_role_in_workspace", return_value=WorkspaceRole.Researcher)
    async def test_get_user_resources_returns_own_user_resources_for_researcher(self, _, __, get_user_resources_mock, app, client, non_admin_user):
        not_my_user_id = "def"
        app.dependency_overrides[get_current_user] = non_admin_user
        my_user_id = non_admin_user().id
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"

        my_user_resource1 = sample_user_resource_object(user_resource_id="a33ad738-7265-4b5f-9eae-a1a62928772a", workspace_id=workspace_id, parent_workspace_service_id=workspace_service_id)
        my_user_resource1.ownerId = my_user_id
        my_user_resource2 = sample_user_resource_object(user_resource_id="b33ad738-7265-4b5f-9eae-a1a62928772a", workspace_id=workspace_id, parent_workspace_service_id=workspace_service_id)
        my_user_resource2.ownerId = my_user_id
        not_my_user_resource = sample_user_resource_object(user_resource_id="c33ad738-7265-4b5f-9eae-a1a62928772a", workspace_id=workspace_id, parent_workspace_service_id=workspace_service_id)
        not_my_user_resource.ownerId = not_my_user_id

        get_user_resources_mock.return_value = [my_user_resource1, my_user_resource2, not_my_user_resource]

        response = await client.get(app.url_path_for(strings.API_GET_MY_USER_RESOURCES, service_id=workspace_service_id))
        assert response.status_code == status.HTTP_200_OK
        actual_returned_resources = response.json()["userResources"]
        assert my_user_resource1 in actual_returned_resources
        assert my_user_resource2 in actual_returned_resources
        assert not_my_user_resource not in actual_returned_resources

        app.dependency_overrides = {}

    @ patch("api.routes.workspaces.UserResourceRepository.get_user_resources_for_workspace_service")
    @ patch("api.routes.workspaces.get_workspace_by_id", return_value=None)
    @ patch("api.routes.workspaces.get_user_role_in_workspace", return_value=WorkspaceRole.NoRole)
    async def test_get_user_resources_raises_403_if_user_is_not_researcher_or_owner(self, _, __, get_user_resources_mock, app, client, non_admin_user):
        app.dependency_overrides[get_current_user] = non_admin_user
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"

        get_user_resources_mock.return_value = [sample_user_resource_object(user_resource_id="a33ad738-7265-4b5f-9eae-a1a62928772a", workspace_id=workspace_id, parent_workspace_service_id=workspace_service_id)]

        response = await client.get(app.url_path_for(strings.API_GET_MY_USER_RESOURCES, service_id=workspace_service_id))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        app.dependency_overrides = {}

    @ patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    @ patch("api.routes.workspaces.get_workspace_by_id", return_value=None)
    @ patch("api.routes.workspaces.get_user_role_in_workspace", return_value=WorkspaceRole.Owner)
    async def test_get_user_resource_returns_a_user_resource_if_found(self, _, __, get_user_resource_mock, app, client, non_admin_user):
        app.dependency_overrides[get_current_user] = non_admin_user
        user_resource_id = "a33ad738-7265-4b5f-9eae-a1a62928772a"
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"
        user_resource = sample_user_resource_object(user_resource_id, workspace_id, workspace_service_id)
        get_user_resource_mock.return_value = user_resource

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE, resource_id=user_resource_id))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["userResource"] == user_resource
        app.dependency_overrides = {}

    @ patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id", side_effect=EntityDoesNotExist)
    @ patch("api.routes.workspaces.get_workspace_by_id", return_value=None)
    @ patch("api.routes.workspaces.get_user_role_in_workspace", return_value=WorkspaceRole.Owner)
    async def test_get_user_resource_raises_404_if_resource_not_found(self, _, __, ___, app, client, non_admin_user):
        app.dependency_overrides[get_current_user] = non_admin_user
        user_resource_id = "a33ad738-7265-4b5f-9eae-a1a62928772a"

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE, resource_id=user_resource_id))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        app.dependency_overrides = {}

    @ patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    @ patch("api.routes.workspaces.get_workspace_by_id", return_value=None)
    @ patch("api.routes.workspaces.get_user_role_in_workspace", return_value=WorkspaceRole.Researcher)
    async def test_get_user_resource_raises_403_if_user_is_researcher_and_not_owner_of_resource(self, _, __, get_user_resource_mock, app, client, non_admin_user):
        app.dependency_overrides[get_current_user] = non_admin_user

        user_resource_id = "a33ad738-7265-4b5f-9eae-a1a62928772a"
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"

        user_resource = sample_user_resource_object(user_resource_id, workspace_id, workspace_service_id)
        user_resource.ownerId = "11111"  # not users id
        get_user_resource_mock.return_value = user_resource

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE, resource_id=user_resource_id))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        app.dependency_overrides = {}

    @ patch("api.dependencies.workspaces.UserResourceRepository.get_user_resource_by_id")
    @ patch("api.routes.workspaces.get_workspace_by_id", return_value=None)
    @ patch("api.routes.workspaces.get_user_role_in_workspace", return_value=WorkspaceRole.NoRole)
    async def test_get_user_resource_raises_403_if_user_is_not_workspace_owner_or_researcher(self, _, __, ___, app, client, non_admin_user):
        app.dependency_overrides[get_current_user] = non_admin_user
        user_resource_id = "a33ad738-7265-4b5f-9eae-a1a62928772a"

        response = await client.get(app.url_path_for(strings.API_GET_USER_RESOURCE, resource_id=user_resource_id))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        app.dependency_overrides = {}


class TestWorkspaceRoutesThatRequireAdminRights:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        app.dependency_overrides[get_current_user] = admin_user
        yield
        app.dependency_overrides = {}

    # [POST] /workspaces/
    @ patch("api.routes.workspaces.send_resource_request_message")
    @ patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @ patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
    async def test_workspaces_post_creates_workspace(self, create_workspace_item_mock, _, __, app, client, workspace_input):
        workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
        create_workspace_item_mock.return_value = sample_workspace(workspace_id)

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["workspaceId"] == workspace_id

    # [POST] /workspaces/
    @ patch("api.routes.workspaces.send_resource_request_message")
    @ patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @ patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
    @ patch("api.routes.workspaces.WorkspaceRepository._validate_resource_parameters")
    async def test_workspaces_post_calls_db_and_service_bus(self, validate_workspace_parameters_mock, create_workspace_item_mock, save_item_mock, send_resource_request_message_mock, app, client, workspace_input):
        workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
        validate_workspace_parameters_mock.return_value = None
        create_workspace_item_mock.return_value = sample_workspace(workspace_id)

        await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        save_item_mock.assert_called_once()
        send_resource_request_message_mock.assert_called_once()

    # [POST] /workspaces/
    @ patch("api.routes.workspaces.send_resource_request_message")
    @ patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @ patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
    @ patch("api.routes.workspaces.WorkspaceRepository._validate_resource_parameters")
    async def test_workspaces_post_returns_202_on_successful_create(self, validate_workspace_parameters_mock, create_workspace_item_mock, _, __, app, client, workspace_input):
        workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
        validate_workspace_parameters_mock.return_value = None
        create_workspace_item_mock.return_value = sample_workspace(workspace_id)

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["workspaceId"] == workspace_id

    # [POST] /workspaces/{workspace_id}/workspace-services
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.send_resource_request_message")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.save_item")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.create_workspace_service_item")
    async def test_workspace_services_post_creates_workspace_service(self, create_workspace_service_item_mock, _, __, get_workspace_mock, app, client, workspace_service_input):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(workspace_id, auth_info_user_in_workspace_owner_role)
        workspace.deployment.status = Status.Deployed
        get_workspace_mock.return_value = workspace

        workspace_service_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
        create_workspace_service_item_mock.return_value = sample_workspace_service(workspace_service_id, workspace_id)

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE, workspace_id=workspace_id), json=workspace_service_input)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["workspaceServiceId"] == workspace_service_id

    # [POST] /workspaces/{workspace_id}/workspace-services
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.create_workspace_service_item", side_effect=ValueError)
    async def test_workspace_services_post_raises_400_bad_request_if_input_is_bad(self, _, get_workspace_mock, app, client, workspace_service_input):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(workspace_id, auth_info_user_in_workspace_owner_role)
        workspace.deployment.status = Status.Deployed
        get_workspace_mock.return_value = workspace

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE_SERVICE, workspace_id=workspace_id), json=workspace_service_input)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_workspace_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id")
    @patch("api.routes.workspaces.UserResourceRepository.create_user_resource_item", side_effect=ValueError)
    async def test_user_resources_post_raises_400_bad_request_if_input_is_bad(self, _, __, get_workspace_mock, app, client, sample_user_resource_input_data):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(workspace_id, auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        input_data = sample_user_resource_input_data

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=workspace_id, service_id=parent_workspace_service_id), json=input_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_workspace_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id")
    @patch("api.routes.workspaces.send_resource_request_message")
    @patch("api.routes.workspaces.UserResourceRepository.save_item")
    @patch("api.routes.workspaces.UserResourceRepository.create_user_resource_item")
    async def test_user_resources_post_creates_user_resource(self, create_user_resource_item_mock, _, __, ___, get_workspace_mock, app, client, sample_user_resource_input_data):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}
        workspace = sample_workspace(workspace_id, auth_info_user_in_workspace_owner_role)
        get_workspace_mock.return_value = workspace

        user_resource_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
        create_user_resource_item_mock.return_value = sample_user_resource_object(user_resource_id, workspace_id, parent_workspace_service_id)
        input_data = sample_user_resource_input_data

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=workspace_id, service_id=parent_workspace_service_id), json=input_data)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["resourceId"] == user_resource_id

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_workspace_id")
    async def test_user_resources_post_with_non_existing_workspace_id_returns_404(self, get_workspace_mock, app, client, sample_user_resource_input_data):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"

        get_workspace_mock.side_effect = EntityDoesNotExist

        input_data = sample_user_resource_input_data
        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=workspace_id, service_id=parent_workspace_service_id), json=input_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_deployed_workspace_by_workspace_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_deployed_workspace_service_by_id")
    async def test_user_resources_post_with_non_existing_service_id_returns_404(self, get_workspace_service_mock, get_workspace_mock, app, client, sample_user_resource_input_data):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"

        workspace = sample_workspace(workspace_id, {})
        get_workspace_mock.return_value = workspace

        get_workspace_service_mock.side_effect = EntityDoesNotExist

        input_data = sample_user_resource_input_data
        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=workspace_id, service_id=parent_workspace_service_id), json=input_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_user_resources_post_with_non_deployed_workspace_id_returns_404(self, get_deployed_workspace_by_workspace_id_mock, app, client, sample_user_resource_input_data):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"

        workspace = sample_workspace(workspace_id, {})
        workspace.deployment.status = Status.Failed
        get_deployed_workspace_by_workspace_id_mock.return_value = workspace

        input_data = sample_user_resource_input_data

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=workspace_id, service_id=parent_workspace_service_id), json=input_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.WORKSPACE_IS_NOT_DEPLOYED

    # [POST] /workspaces/{workspace_id}/workspace-services/{service_id}/user-resources
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    async def test_user_resources_post_with_non_deployed_service_id_returns_404(self, get_workspace_service_mock, get_workspace_mock, app, client, sample_user_resource_input_data):
        workspace_id = "98b8799a-7281-4fc5-91d5-49684a4810ff"
        parent_workspace_service_id = "937453d3-82da-4bfc-b6e9-9a7853ef753e"

        workspace = sample_workspace(workspace_id, {})
        workspace.deployment.status = Status.Deployed
        get_workspace_mock.return_value = workspace

        workspace_service = sample_workspace_service(workspace_id, parent_workspace_service_id)
        workspace_service.deployment.status = Status.Failed
        get_workspace_service_mock.return_value = workspace_service

        input_data = sample_user_resource_input_data

        response = await client.post(app.url_path_for(strings.API_CREATE_USER_RESOURCE, workspace_id=workspace_id, service_id=parent_workspace_service_id), json=input_data)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.text == strings.WORKSPACE_SERVICE_IS_NOT_DEPLOYED

    # [POST] /workspaces/
    @ patch("api.routes.workspaces.WorkspaceRepository.delete_item")
    @ patch("api.routes.workspaces.send_resource_request_message")
    @ patch("api.routes.workspaces.WorkspaceRepository.save_item")
    @ patch("api.routes.workspaces.WorkspaceRepository.create_workspace_item")
    @ patch("api.routes.workspaces.WorkspaceRepository._validate_resource_parameters")
    async def test_workspaces_post_returns_503_if_service_bus_call_fails(self, validate_workspace_parameters_mock, create_workspace_item_mock, _, send_resource_request_message_mock, delete_item_mock, app, client, workspace_input):
        workspace_id = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
        validate_workspace_parameters_mock.return_value = None
        create_workspace_item_mock.return_value = sample_workspace(workspace_id)
        send_resource_request_message_mock.side_effect = Exception

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        delete_item_mock.assert_called_once_with(workspace_id)

    # [POST] /workspaces/
    @ patch("api.routes.workspaces.WorkspaceRepository.validate_input_against_template")
    async def test_workspaces_post_returns_400_if_template_does_not_exist(self, validate_input_mock, app, client, workspace_input):
        validate_input_mock.side_effect = ValueError

        response = await client.post(app.url_path_for(strings.API_CREATE_WORKSPACE), json=workspace_input)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [PATCH] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspaces_patch_returns_404_if_workspace_does_not_exist(self, get_workspace_mock, app, client):
        get_workspace_mock.side_effect = EntityDoesNotExist
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"

        input_data = '{"enabled": true}'

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=workspace_id), json=input_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceRepository.patch_workspace")
    async def test_workspaces_patch_patches_workspace(self, patch_workspace_mock, get_workspace_mock, app, client):
        workspace_to_patch = sample_workspace("933ad738-7265-4b5f-9eae-a1a62928772e")
        patch_workspace_mock.return_value = None
        get_workspace_mock.return_value = workspace_to_patch
        workspace_patch = {"enabled": True}

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE, workspace_id=workspace_to_patch.id), json=workspace_patch)
        patch_workspace_mock.assert_called_once_with(workspace_to_patch, workspace_patch)

        assert response.status_code == status.HTTP_200_OK

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    async def test_workspaces_service_patch_returns_404_if_workspace_service_does_not_exist(self, get_workspace_service_mock, app, client):
        get_workspace_service_mock.side_effect = EntityDoesNotExist

        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"

        input_data = '{"enabled": true}'
        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=workspace_id, service_id=workspace_service_id), json=input_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspaces_service_patch_returns_404_if_workspace_does_not_exist(self, get_workspace_mock, get_workspace_service_mock, app, client):
        get_workspace_mock.side_effect = EntityDoesNotExist

        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"

        workspace_service_to_patch = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service_to_patch
        input_data = '{"enabled": true}'

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=workspace_id, service_id=workspace_service_id), json=input_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspaces_service_patch_returns_422_if_invalid_service_id(self, get_workspace_mock, get_workspace_service_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "IAmNotEvenAGUID!"

        workspace_service_to_patch = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service_to_patch
        get_workspace_mock.return_value = sample_deployed_workspace(workspace_id)

        workspace_service_patch = {"enabled": True}
        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=workspace_id, service_id=workspace_service_id), json=workspace_service_patch)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspaces_service_patch_returns_422_if_invalid_ws_id(self, get_workspace_mock, get_workspace_service_mock, app, client):
        workspace_id = "IAmNotEvenAGUID!"
        workspace_service_id = "933ad738-7265-4b5f-9eae-a1a62928772e"

        workspace_service_to_patch = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service_to_patch
        get_workspace_mock.return_value = sample_deployed_workspace(workspace_id)

        workspace_service_patch = {"enabled": True}
        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=workspace_id, service_id=workspace_service_id), json=workspace_service_patch)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # [PATCH] /workspaces/{workspace_id}/services/{service_id}
    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.patch_workspace_service")
    async def test_workspaces_services_patch_patches_workspace(self, patch_workspace_service_mock, get_workspace_mock, get_workspace_service_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"

        auth_info_user_in_workspace_owner_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab124', 'WorkspaceResearcher': 'ab125'}}

        patch_workspace_service_mock.return_value = None

        workspace_service_to_patch = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service_to_patch
        get_workspace_mock.return_value = sample_deployed_workspace(workspace_id, auth_info_user_in_workspace_owner_role)

        workspace_service_patch = {"enabled": True}

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=workspace_id, service_id=workspace_service_id), json=workspace_service_patch)
        patch_workspace_service_mock.assert_called_once_with(workspace_service_to_patch, workspace_service_patch)

        assert response.status_code == status.HTTP_200_OK

    @ patch("api.dependencies.workspaces.WorkspaceServiceRepository.get_workspace_service_by_id")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.patch_workspace_service")
    async def test_workspaces_services_patch_is_not_allowed_for_non_ws_owners(self, patch_workspace_service_mock, get_workspace_mock, get_workspace_service_mock, app, client) -> None:
        workspace_id = "abcad738-7265-4b5f-9eae-a1a62928772e"
        workspace_service_id = "abcad738-7265-4b5f-9eae-a1a62928772e"

        auth_info_user_in_workspace_researcher_role = {'sp_id': 'ab123', 'roles': {'WorkspaceOwner': 'ab127', 'WorkspaceResearcher': workspace_id}}
        patch_workspace_service_mock.return_value = None
        workspace_service_to_patch = sample_workspace_service(workspace_service_id, workspace_id)
        get_workspace_service_mock.return_value = workspace_service_to_patch
        get_workspace_mock.return_value = sample_deployed_workspace(workspace_id, auth_info_user_in_workspace_researcher_role)

        workspace_service_patch = {"enabled": True}

        response = await client.patch(app.url_path_for(strings.API_UPDATE_WORKSPACE_SERVICE, workspace_id=workspace_id, service_id=workspace_service_id), json=workspace_service_patch)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # [DELETE] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    async def test_workspace_delete_returns_400_if_workspace_is_enabled(self, get_workspace_mock, app, client):
        workspace_id = "933ad738-7265-4b5f-9eae-a1a62928772e"
        workspace = sample_workspace(workspace_id)
        workspace.resourceTemplateParameters["enabled"] = True
        get_workspace_mock.return_value = workspace

        response = await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id=workspace_id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [DELETE] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace")
    async def test_workspace_delete_returns_400_if_associated_workspace_services_are_not_deleted(self, get_active_workspace_services_for_workspace_mock, get_workspace_mock, disabled_workspace, app, client):
        get_workspace_mock.return_value = disabled_workspace
        get_active_workspace_services_for_workspace_mock.return_value = ["some workspace service that is not deleted"]

        response = await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id="933ad738-7265-4b5f-9eae-a1a62928772e"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # [DELETE] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.get_repository")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace")
    @ patch('azure.cosmos.CosmosClient')
    @ patch('api.routes.workspaces.WorkspaceRepository.mark_resource_as_deleting')
    @ patch('api.routes.workspaces.send_resource_request_message')
    async def test_workspace_delete_deletes_workspace(self, _, delete_workspace_mock, cosmos_client_mock, get_active_workspace_services_for_workspace_mock, get_workspace_mock, get_repository_mock, disabled_workspace, app, client):
        get_workspace_mock.return_value = disabled_workspace
        get_active_workspace_services_for_workspace_mock.return_value = []
        get_repository_mock.side_effects = [WorkspaceRepository(cosmos_client_mock), WorkspaceServiceRepository(cosmos_client_mock)]

        await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id="933ad738-7265-4b5f-9eae-a1a62928772e"))

        delete_workspace_mock.assert_called_once()

    # [DELETE] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.get_repository")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace")
    @ patch('azure.cosmos.CosmosClient')
    @ patch('api.routes.workspaces.WorkspaceRepository.mark_resource_as_deleting')
    @ patch('api.routes.workspaces.send_resource_request_message')
    async def test_workspace_delete_sends_a_request_message_to_uninstall_the_workspace(self, send_request_message_mock, _, cosmos_client_mock, get_active_workspace_services_for_workspace_mock, get_workspace_mock, get_repository_mock, disabled_workspace, app, client):
        get_workspace_mock.return_value = disabled_workspace
        get_active_workspace_services_for_workspace_mock.return_value = []
        get_repository_mock.side_effects = [WorkspaceRepository(cosmos_client_mock), WorkspaceServiceRepository(cosmos_client_mock)]

        await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id="933ad738-7265-4b5f-9eae-a1a62928772e"))

        send_request_message_mock.assert_called_once()

    # [DELETE] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.get_repository")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace")
    @ patch('azure.cosmos.CosmosClient')
    @ patch('api.routes.workspaces.WorkspaceRepository.mark_resource_as_deleting')
    @ patch('api.routes.workspaces.send_resource_request_message')
    @ patch('api.routes.workspaces.WorkspaceRepository.restore_previous_deletion_state')
    async def test_workspace_delete_reverts_the_workspace_if_service_bus_call_fails(self, restore_previous_deletion_state_mock, send_request_message_mock, _, cosmos_client_mock, get_active_workspace_services_for_workspace_mock, get_workspace_mock, get_repository_mock, disabled_workspace, app, client):
        get_workspace_mock.return_value = disabled_workspace
        get_active_workspace_services_for_workspace_mock.return_value = []
        get_repository_mock.side_effects = [WorkspaceRepository(cosmos_client_mock), WorkspaceServiceRepository(cosmos_client_mock)]
        send_request_message_mock.side_effect = Exception

        await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id="933ad738-7265-4b5f-9eae-a1a62928772e"))

        # assert we revert the workspace
        restore_previous_deletion_state_mock.assert_called_once()

    # [DELETE] /workspaces/{workspace_id}
    @ patch("api.dependencies.workspaces.get_repository")
    @ patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_workspace_id")
    @ patch("api.routes.workspaces.WorkspaceServiceRepository.get_active_workspace_services_for_workspace")
    @ patch('azure.cosmos.CosmosClient')
    @ patch('api.routes.workspaces.WorkspaceRepository.mark_resource_as_deleting', side_effect=Exception)
    async def test_workspace_delete_raises_503_if_marking_the_resource_as_deleted_in_the_db_fails(self, _, __, ___, get_workspace_mock, _____, client, app, disabled_workspace):
        get_workspace_mock.return_value = disabled_workspace

        response = await client.delete(app.url_path_for(strings.API_DELETE_WORKSPACE, workspace_id="933ad738-7265-4b5f-9eae-a1a62928772e"))

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
