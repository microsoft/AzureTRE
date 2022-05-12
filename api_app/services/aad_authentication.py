import base64
import logging
from typing import List
import jwt
import requests
import rsa

from fastapi import Request, HTTPException, status
from msal import ConfidentialClientApplication

from services.access_service import AccessService, AuthConfigValidationError
from core import config
from db.errors import EntityDoesNotExist
from models.domain.authentication import User, RoleAssignment
from models.domain.workspace import Workspace, WorkspaceRole
from resources import strings
from api.dependencies.database import get_db_client_from_request
from db.repositories.workspaces import WorkspaceRepository


class AzureADAuthorization(AccessService):
    _jwt_keys: dict = {}

    require_one_of_roles = None

    TRE_CORE_ROLES = ['TREAdmin', 'TREUser']
    WORKSPACE_ROLES_DICT = {'WorkspaceOwner': 'app_role_id_workspace_owner', 'WorkspaceResearcher': 'app_role_id_workspace_researcher'}

    def __init__(self, auto_error: bool = True, require_one_of_roles: list = None):
        super(AzureADAuthorization, self).__init__(
            authorizationUrl=f"{config.AAD_INSTANCE}/{config.AAD_TENANT_ID}/oauth2/v2.0/authorize",
            tokenUrl=f"{config.AAD_INSTANCE}/{config.AAD_TENANT_ID}/oauth2/v2.0/token",
            refreshUrl=f"{config.AAD_INSTANCE}/{config.AAD_TENANT_ID}/oauth2/v2.0/token",
            scheme_name="oauth2",
            auto_error=auto_error
        )
        self.require_one_of_roles = require_one_of_roles

    async def __call__(self, request: Request) -> User:

        token: str = await super(AzureADAuthorization, self).__call__(request)

        decoded_token = None

        # Try workspace app registration if appropriate
        if 'workspace_id' in request.path_params and any(role in self.require_one_of_roles for role in self.WORKSPACE_ROLES_DICT.keys()):
            # as we have a workspace_id not given, try decoding token
            logging.debug("Workspace ID was provided. Getting Workspace API app registration")
            try:
                app_reg_id = self._fetch_ws_app_reg_id_from_ws_id(request)
                decoded_token = self._decode_token(token, app_reg_id)
            except Exception as e:
                logging.debug(e)
                logging.debug("Failed to decode using workspace_id, trying with TRE API app registration")
                pass

        # Try TRE API app registration if appropriate
        if decoded_token is None and any(role in self.require_one_of_roles for role in self.TRE_CORE_ROLES):
            try:
                decoded_token = self._decode_token(token, config.API_AUDIENCE)
            except jwt.exceptions.InvalidSignatureError:
                logging.debug("Failed to decode using TRE API app registration")
                pass

        # Failed to decode token using either app registration
        if decoded_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_UNABLE_TO_VALIDATE_TOKEN)

        try:
            user = self._get_user_from_token(decoded_token)
        except Exception as e:
            logging.debug(e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER, headers={"WWW-Authenticate": "Bearer"})

        try:
            if not any(role in self.require_one_of_roles for role in user.roles):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {self.require_one_of_roles}', headers={"WWW-Authenticate": "Bearer"})
        except Exception as e:
            logging.debug(e)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {self.require_one_of_roles}', headers={"WWW-Authenticate": "Bearer"})

        return user

    @staticmethod
    def _fetch_ws_app_reg_id_from_ws_id(request: Request) -> str:
        workspace_id = None
        if "workspace_id" not in request.path_params:
            logging.error("Neither a workspace ID nor a default app registration id were provided")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS)
        try:
            workspace_id = request.path_params['workspace_id']
            ws_repo = WorkspaceRepository(get_db_client_from_request(request))
            workspace = ws_repo.get_workspace_by_id(workspace_id)
            ws_app_reg_id = workspace.properties['client_id']

            return ws_app_reg_id
        except EntityDoesNotExist as e:
            logging.error(e)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)
        except Exception as e:
            logging.error(e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS)

    @staticmethod
    def _get_user_from_token(decoded_token: dict) -> User:
        user_id = decoded_token['oid']

        return User(id=user_id,
                    name=decoded_token.get('name', ''),
                    email=decoded_token.get('email', ''),
                    roles=decoded_token.get('roles', []))

    def _decode_token(self, token: str, ws_app_reg_id: str) -> dict:
        key_id = self._get_key_id(token)
        key = self._get_token_key(key_id)

        logging.debug("workspace app registration id: %s", ws_app_reg_id)
        return jwt.decode(token, key, options={"verify_signature": True}, algorithms=['RS256'], audience=ws_app_reg_id)

    @staticmethod
    def _get_key_id(token: str) -> str:
        headers = jwt.get_unverified_header(token)
        return headers['kid'] if headers and 'kid' in headers else None

    @staticmethod
    def _ensure_b64padding(key: str) -> str:
        """
        The base64 encoded keys are not always correctly padded, so pad with the right number of =
        """
        key = key.encode('utf-8')
        missing_padding = len(key) % 4
        for _ in range(missing_padding):
            key = key + b'='
        return key

    def _get_token_key(self, key_id: str) -> str:
        """
        Rather tha use PyJWKClient.get_signing_key_from_jwt every time, we'll get all the keys from AAD and cache them.
        """
        if key_id not in AzureADAuthorization._jwt_keys:
            response = requests.get(f"{config.AAD_INSTANCE}/{config.AAD_TENANT_ID}/v2.0/.well-known/openid-configuration")
            aad_metadata = response.json() if response.ok else None
            jwks_uri = aad_metadata['jwks_uri'] if aad_metadata and 'jwks_uri' in aad_metadata else None
            if jwks_uri:
                response = requests.get(jwks_uri)
                keys = response.json() if response.ok else None
                if keys and 'keys' in keys:
                    for key in keys['keys']:
                        n = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['n'])), "big")
                        e = int.from_bytes(base64.urlsafe_b64decode(self._ensure_b64padding(key['e'])), "big")
                        pub_key = rsa.PublicKey(n, e)
                        # Cache the PEM formatted public key.
                        AzureADAuthorization._jwt_keys[key['kid']] = pub_key.save_pkcs1()

        return AzureADAuthorization._jwt_keys[key_id]

    # The below functions are needed to list which workspaces a specific user has access to i.e. GET /workspaces.
    # The below functions require Directory.ReadAll permissions on AzureAD.
    # If there is no need to list all workspaces for a specific user, then Directory.ReadAll permissions are not required.
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
    def _get_service_principal_endpoint(client_id) -> str:
        return f"https://graph.microsoft.com/v1.0/serviceprincipals?$filter=appid eq '{client_id}'"

    def _get_app_sp_graph_data(self, client_id: str) -> dict:
        msgraph_token = self._get_msgraph_token()
        sp_endpoint = self._get_service_principal_endpoint(client_id)
        graph_data = requests.get(sp_endpoint, headers=self._get_auth_header(msgraph_token)).json()
        return graph_data

    # This method is called when you create a workspace and you already have an AAD App Registration
    # to link it to. You pass in teh client_id and go and get the extra information you need from AAD
    # If the client_id is `auto_create`, then these values will be written by Terraform.
    def _get_app_auth_info(self, client_id: str) -> dict:
        graph_data = self._get_app_sp_graph_data(client_id)
        if 'value' not in graph_data or len(graph_data['value']) == 0:
            logging.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_INFO_FOR_APP} {client_id}")

        app_info = graph_data['value'][0]
        authInfo = {'sp_id': app_info['id'], 'scope_id': app_info['servicePrincipalNames'][0]}

        # Convert the roles into ids (We could have more roles defined in the app than we need.)
        for appRole in app_info['appRoles']:
            if appRole['value'] in self.WORKSPACE_ROLES_DICT.keys():
                authInfo[self.WORKSPACE_ROLES_DICT[appRole['value']]] = appRole['id']

        return authInfo

    def _get_role_assignment_graph_data(self, user_id: str) -> dict:
        msgraph_token = self._get_msgraph_token()
        user_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments"
        graph_data = requests.get(user_endpoint, headers=self._get_auth_header(msgraph_token)).json()
        return graph_data

    def extract_workspace_auth_information(self, data: dict) -> dict:
        if "client_id" not in data:
            raise AuthConfigValidationError(strings.ACCESS_PLEASE_SUPPLY_CLIENT_ID)

        auth_info = {}
        # The user may want us to create the AAD workspace app and therefore they
        # don't know the client_id yet.
        if data["client_id"] != "auto_create":
            auth_info = self._get_app_auth_info(data["client_id"])

            # Check we've get all our required roles
            for role in self.WORKSPACE_ROLES_DICT.items():
                if role[1] not in auth_info:
                    raise AuthConfigValidationError(f"{strings.ACCESS_APP_IS_MISSING_ROLE} {role[0]}")

        return auth_info

    def get_user_role_assignments(self, user_id: str) -> List[RoleAssignment]:
        graph_data = self._get_role_assignment_graph_data(user_id)

        if 'value' not in graph_data:
            logging.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER} {user_id}")

        return [RoleAssignment(role_assignment['resourceId'], role_assignment['appRoleId']) for role_assignment in graph_data['value']]

    def get_workspace_role(self, user: User, workspace: Workspace, user_role_assignments: List[RoleAssignment]) -> WorkspaceRole:
        if 'sp_id' not in workspace.properties:
            raise AuthConfigValidationError(strings.AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE)

        workspace_sp_id = workspace.properties['sp_id']

        for requiredRole in self.WORKSPACE_ROLES_DICT.values():
            if requiredRole not in workspace.properties:
                raise AuthConfigValidationError(strings.AUTH_CONFIGURATION_NOT_AVAILABLE_FOR_WORKSPACE)

        if RoleAssignment(resource_id=workspace_sp_id, role_id=workspace.properties['app_role_id_workspace_owner']) in user_role_assignments:
            return WorkspaceRole.Owner
        if RoleAssignment(resource_id=workspace_sp_id, role_id=workspace.properties['app_role_id_workspace_researcher']) in user_role_assignments:
            return WorkspaceRole.Researcher
        return WorkspaceRole.NoRole
