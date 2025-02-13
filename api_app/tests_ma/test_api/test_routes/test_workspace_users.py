from unittest.mock import AsyncMock
import pytest
from mock import patch

from fastapi import status

from models.domain.authentication import Role, User
from tests_ma.test_api.test_routes.test_resource_helpers import FAKE_CREATE_TIMESTAMP
from tests_ma.test_api.conftest import create_admin_user
from services.authentication import get_current_admin_user, \
    get_current_tre_user_or_tre_admin, \
    get_current_workspace_owner_or_researcher_user_or_airlock_manager, \
    get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin

from models.domain.workspace import Workspace
from resources import strings

pytestmark = pytest.mark.asyncio


WORKSPACE_ID = '933ad738-7265-4b5f-9eae-a1a62928772e'
SERVICE_ID = 'abcad738-7265-4b5f-9eae-a1a62928772e'
USER_RESOURCE_ID = 'a33ad738-7265-4b5f-9eae-a1a62928772a'
CLIENT_ID = 'f0acf127-a672-a672-a672-a15e5bf9f127'
OPERATION_ID = '11111111-7265-4b5f-9eae-a1a62928772f'

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


class TestWorkspaceUserRoutesWithTreAdmin:
    @pytest.fixture(autouse=True, scope='class')
    def _prepare(self, app, admin_user):
        with patch('services.aad_authentication.AzureADAuthorization._get_user_from_token', return_value=admin_user()):
            app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager_or_tre_admin] = admin_user
            app.dependency_overrides[get_current_tre_user_or_tre_admin] = admin_user
            app.dependency_overrides[get_current_workspace_owner_or_researcher_user_or_airlock_manager] = admin_user
            app.dependency_overrides[get_current_admin_user] = admin_user
            yield
            app.dependency_overrides = {}

    @pytest.mark.parametrize("auth_class", ["aad_authentication.AzureADAuthorization"])
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_get_workspace_users_returns_users(self, _, auth_class, app, client):
        with patch(f"services.{auth_class}.get_workspace_users") as get_workspace_users_mock:

            users = [
                {
                    "id": "123",
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "roles": ["WorkspaceOwner", "WorkspaceResearcher"],
                    'roleAssignments': []
                },
                {
                    "id": "456",
                    "name": "Jane Smith",
                    "email": "jane.smith@example.com",
                    "roles": ["WorkspaceResearcher"],
                    'roleAssignments': []
                }
            ]
            get_workspace_users_mock.return_value = users

            response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_USERS, workspace_id=WORKSPACE_ID))

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["users"] == users


    @pytest.mark.parametrize("auth_class", ["aad_authentication.AzureADAuthorization"])
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_assign_workspace_user_assigns_workspace_user(self, get_workspace_by_id_mock, auth_class, app, client):
        with patch(f"services.{auth_class}.get_user_by_email") as get_user_by_email_mock, \
            patch(f"services.{auth_class}.get_workspace_role_by_name") as get_workspace_role_by_name_mock, \
            patch(f"services.{auth_class}.assign_workspace_user") as assign_workspace_user_mock, \
            patch(f"services.{auth_class}.get_workspace_users") as get_workspace_users_mock:

            workspace = get_workspace_by_id_mock.return_value

            user = {
                "id": "123",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "roles": ["WorkspaceOwner", "WorkspaceResearcher"],
                "roleAssignments": []
            }

            users = [user]

            role_name_to_assign = "AirlockManager"
            role = {"id": "test_role_id"}

            get_user_by_email_mock.return_value = User.parse_obj(user)
            get_workspace_role_by_name_mock.return_value = role
            get_workspace_users_mock.return_value = users

            response = await client.post(app.url_path_for(strings.API_ASSIGN_WORKSPACE_USER, workspace_id=WORKSPACE_ID), params={"user_email": user["email"], "role_name": role_name_to_assign})
            assert response.status_code == status.HTTP_202_ACCEPTED

            get_user_by_email_mock.assert_called_once_with(user["email"])
            get_workspace_role_by_name_mock.assert_called_once_with(role_name_to_assign, workspace)
            assign_workspace_user_mock.assert_called_once_with(user, workspace, role)
            get_workspace_users_mock.assert_called_once()

            assert response.json()["users"] == users

    @pytest.mark.parametrize("auth_class", ["aad_authentication.AzureADAuthorization"])
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_remove_workspace_user_assignment_removes_workspace_user_assignment(self, get_workspace_by_id_mock, auth_class, app, client):
        with patch(f"services.{auth_class}.remove_workspace_role_user_assignment") as remove_workspace_role_user_assignment_mock, \
            patch(f"services.{auth_class}.get_user_by_email") as get_user_by_email_mock, \
            patch(f"services.{auth_class}.get_workspace_role_by_name") as get_workspace_role_by_name_mock, \
            patch(f"services.{auth_class}.get_workspace_users") as get_workspace_users_mock:

            workspace = get_workspace_by_id_mock.return_value

            user = {
                "id": "123",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "roles": ["WorkspaceOwner", "WorkspaceResearcher"],
                "roleAssignments": []
            }

            role_name_to_deassign = "WorkspaceResearcher"
            role = {"id": "test_role_id"}

            get_user_by_email_mock.return_value = User.parse_obj(user)
            get_workspace_role_by_name_mock.return_value = role

            user["roles"].remove(role_name_to_deassign)
            users = [user]

            get_workspace_users_mock.return_value = users

            response = await client.delete(app.url_path_for(strings.API_ASSIGN_WORKSPACE_USER, workspace_id=WORKSPACE_ID), params={"user_email": user["email"], "role_name": role_name_to_deassign})
            assert response.status_code == status.HTTP_202_ACCEPTED

            get_user_by_email_mock.assert_called_once_with(user["email"])
            get_workspace_role_by_name_mock.assert_called_once_with(role_name_to_deassign, workspace)
            remove_workspace_role_user_assignment_mock.assert_called_once_with(get_user_by_email_mock.return_value, role, workspace)
            get_workspace_users_mock.assert_called_once()

            assert response.json()["users"] == users

    @pytest.mark.parametrize("auth_class", ["aad_authentication.AzureADAuthorization"])
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_get_assignable_users_returns_assignable_users(self, get_workspace_by_id_mock, auth_class, app, client):
        with patch(f"services.{auth_class}.get_assignable_users") as get_assignable_users_mock:
            assignable_users = [
                {
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                },
                {
                    "name": "Jane Smith",
                    "email": "jane.smith@example.com",
                }
            ]

            get_assignable_users_mock.return_value = assignable_users

            response = await client.get(app.url_path_for(strings.API_GET_ASSIGNABLE_USERS, workspace_id=WORKSPACE_ID))

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["assignable_users"] == assignable_users


    @pytest.mark.parametrize("auth_class", ["aad_authentication.AzureADAuthorization"])
    @patch("api.dependencies.workspaces.WorkspaceRepository.get_workspace_by_id", return_value=sample_workspace())
    async def test_get_workspace_roles_returns_workspace_roles(self, get_workspace_by_id_mock, auth_class, app, client):
        with patch(f"services.{auth_class}.get_workspace_roles") as get_workspace_roles_mock:
            workspace_roles = [
                Role(
                    id="1",
                    value="AirlockManager",
                    isEnabled=True,
                    email=None,
                    allowedMemberTypes=["Application", "User"],
                    description="Provides airlock managers access to the Workspace and ability to review airlock requests.",
                    displayName="Airlock Manager",
                    origin="Application",
                    roleAssignments=[],
                ),
                Role(
                    id="2",
                    value="WorkspaceResearcher",
                    isEnabled=True,
                    email=None,
                    allowedMemberTypes=["Application", "User"],
                    description="Provides researchers access to the Workspace.",
                    displayName="Workspace Researcher",
                    origin="Application",
                    roleAssignments=[],
                ),
                Role(
                    id="3",
                    value="WorkspaceOwner",
                    isEnabled=True,
                    email=None,
                    allowedMemberTypes=["Application", "User"],
                    description="Provides workspace owners access to the Workspace.",
                    displayName="Workspace Owner",
                    origin="Application",
                    roleAssignments=[],
                ),
            ]

            get_workspace_roles_mock.return_value = workspace_roles

            response = await client.get(app.url_path_for(strings.API_GET_WORKSPACE_ROLES, workspace_id=WORKSPACE_ID))

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["roles"] == workspace_roles
