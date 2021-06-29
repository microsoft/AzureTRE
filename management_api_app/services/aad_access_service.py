import logging

import requests
from msal import ConfidentialClientApplication

from core import config
from models.domain.workspace import Workspace, WorkspaceRole
from resources import strings
from services.access_service import AccessService, AuthConfigValidationError
from services.authentication import User


class AADAccessService(AccessService):
    @staticmethod
    def _get_msgraph_token() -> str:
        scopes = ["https://graph.microsoft.com/.default"]
        app = ConfidentialClientApplication(client_id=config.API_CLIENT_ID, client_credential=config.API_CLIENT_SECRET, authority=f"{config.AAD_INSTANCE}/{config.AAD_TENANT_ID}")
        result = app.acquire_token_silent(scopes=scopes, account=None)
        if not result:
            logging.info('No suitable token exists in cache, getting a new one from AAD')
            result = app.acquire_token_for_client(scopes=scopes)
        if "access_token" not in result:
            logging.debug(result.get('error'))
            logging.debug(result.get('error_description'))
            logging.debug(result.get('correlation_id'))
            raise Exception(result.get('error'))
        return result["access_token"]

    @staticmethod
    def _get_auth_header(msgraph_token: str) -> dict:
        return {'Authorization': 'Bearer ' + msgraph_token}

    @staticmethod
    def _get_service_principal_endpoint(app_id) -> str:
        return f"https://graph.microsoft.com/v1.0/serviceprincipals?$filter=appid eq '{app_id}'"

    def _get_app_sp_graph_data(self, app_id: str) -> dict:
        msgraph_token = self._get_msgraph_token()
        sp_endpoint = self._get_service_principal_endpoint(app_id)
        graph_data = requests.get(sp_endpoint, headers=self._get_auth_header(msgraph_token)).json()
        return graph_data

    def _get_app_auth_info(self, app_id: str) -> dict:
        graph_data = self._get_app_sp_graph_data(app_id)
        if 'value' not in graph_data or len(graph_data['value']) == 0:
            logging.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_INFO_FOR_APP} {app_id}")

        app_info = graph_data['value'][0]
        sp_id = app_info['id']
        roles = app_info['appRoles']

        return {
            'sp_id': sp_id,
            'roles': {role['value']: role['id'] for role in roles}
        }

    def _get_role_assignment_graph_data(self, user_id: str) -> dict:
        msgraph_token = self._get_msgraph_token()
        user_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments"
        graph_data = requests.get(user_endpoint, headers=self._get_auth_header(msgraph_token)).json()
        return graph_data

    def extract_workspace_auth_information(self, data: dict) -> dict:
        if "app_id" not in data:
            raise AuthConfigValidationError(strings.ACCESS_PLEASE_SUPPLY_APP_ID)

        auth_info = self._get_app_auth_info(data["app_id"])

        for role in ['WorkspaceOwner', 'WorkspaceResearcher']:
            if role not in auth_info['roles']:
                raise AuthConfigValidationError(f"{strings.ACCESS_APP_IS_MISSING_ROLE} {role}")

        return auth_info

    def get_user_role_assignments(self, user_id: str) -> dict:
        graph_data = self._get_role_assignment_graph_data(user_id)

        if 'value' not in graph_data:
            logging.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER} {user_id}")

        return {role_assignment['resourceId']: role_assignment['appRoleId'] for role_assignment in graph_data['value']}

    @staticmethod
    def get_workspace_role(user: User, workspace: Workspace) -> WorkspaceRole:
        if 'sp_id' not in workspace.authInformation or 'roles' not in workspace.authInformation:
            raise AuthConfigValidationError(strings.AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE)

        workspace_sp_id = workspace.authInformation['sp_id']
        workspace_roles = workspace.authInformation['roles']

        if 'WorkspaceOwner' not in workspace_roles or 'WorkspaceResearcher' not in workspace_roles:
            raise AuthConfigValidationError(strings.AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE)

        if workspace_sp_id in user.roleAssignments:
            if workspace_roles['WorkspaceOwner'] == user.roleAssignments[workspace_sp_id]:
                return WorkspaceRole.Owner
            if workspace_roles['WorkspaceResearcher'] == user.roleAssignments[workspace_sp_id]:
                return WorkspaceRole.Researcher
        return WorkspaceRole.NoRole
