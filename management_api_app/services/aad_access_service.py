import logging

import requests
from msal import ConfidentialClientApplication

from core import config
from services.access_service import AccessService, AuthConfigValidationError


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
            # TODO: Better error message + strings + should this be another type of error?
            logging.debug(result.get('error'))
            logging.debug(result.get('error_description'))
            logging.debug(result.get('correlation_id'))
            raise AuthConfigValidationError("Can't get access token")
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
            raise AuthConfigValidationError(f"Unable to get app info for app: {app_id}")

        app_info = graph_data['value'][0]
        sp_id = app_info['id']
        roles = app_info['appRoles']

        return {
            'sp_id': sp_id,
            'roles': {role['value']: role['id'] for role in roles}
        }

    def extract_workspace_auth_information(self, data: dict) -> dict:
        if "app_id" not in data:
            raise AuthConfigValidationError("Please supply the app_id for the AAD application")

        auth_info = self._get_app_auth_info(data["app_id"])
        print(auth_info)

        for role in ['TREOwner', 'TREResearcher']:
            if role not in auth_info['roles']:
                raise AuthConfigValidationError(f"App is missing the role {role}")

        return auth_info
