import base64
import logging
from collections import defaultdict
from enum import Enum
from typing import List, Optional
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


class PrincipalType(Enum):
    User = "User"
    Group = "Group"
    ServicePrincipal = "ServicePrincipal"


class AzureADAuthorization(AccessService):
    _jwt_keys: dict = {}

    require_one_of_roles = None

    TRE_CORE_ROLES = ['TREAdmin', 'TREUser']
    WORKSPACE_ROLES_DICT = {'WorkspaceOwner': 'app_role_id_workspace_owner', 'WorkspaceResearcher': 'app_role_id_workspace_researcher', 'AirlockManager': 'app_role_id_workspace_airlock_manager'}

    def __init__(self, auto_error: bool = True, require_one_of_roles: Optional[list] = None):
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
                # get the app reg id - which might be blank if the workspace hasn't fully created yet.
                # if it's blank, don't use workspace auth, use core auth - and a TRE Admin can still get it
                app_reg_id = await self._fetch_ws_app_reg_id_from_ws_id(request)
                if app_reg_id != "":
                    decoded_token = self._decode_token(token, app_reg_id)
            except HTTPException as h:
                raise h
            except Exception as e:
                logging.debug(e)
                logging.debug("Failed to decode using workspace_id, trying with TRE API app registration")
                pass

        # Try TRE API app registration if appropriate
        if decoded_token is None and any(role in self.require_one_of_roles for role in self.TRE_CORE_ROLES):
            try:
                decoded_token = self._decode_token(token, config.API_AUDIENCE)
            except jwt.exceptions.InvalidSignatureError:
                logging.debug("Failed to decode using TRE API app registration (Invalid Signatrue)")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.INVALID_SIGNATURE)
            except jwt.exceptions.ExpiredSignatureError:
                logging.debug("Failed to decode using TRE API app registration (Expired Signature)")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.EXPIRED_SIGNATURE)
            except jwt.exceptions.InvalidTokenError:
                # any other token validation exception, we want to catch all of these...
                logging.debug("Failed to decode using TRE API app registration (Invalid token)")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.INVALID_TOKEN)
            except Exception as e:
                # Unexpected token decoding/validation exception. making sure we are not crashing (with 500)
                logging.debug(e)
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
    async def _fetch_ws_app_reg_id_from_ws_id(request: Request) -> str:
        workspace_id = None
        if "workspace_id" not in request.path_params:
            logging.error("Neither a workspace ID nor a default app registration id were provided")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS)
        try:
            workspace_id = request.path_params['workspace_id']
            db_client = await get_db_client_from_request(request)
            ws_repo = await WorkspaceRepository.create(db_client)
            workspace = await ws_repo.get_workspace_by_id(workspace_id)

            ws_app_reg_id = ""
            if "client_id" in workspace.properties:
                ws_app_reg_id = workspace.properties['client_id']

            return ws_app_reg_id
        except EntityDoesNotExist:
            logging.exception(strings.WORKSPACE_DOES_NOT_EXIST)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=strings.WORKSPACE_DOES_NOT_EXIST)
        except Exception:
            logging.exception(f"Failed to get workspace app registration ID for workspace {workspace_id}")
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
            logging.debug('No suitable token exists in cache, getting a new one from AAD')
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

    @staticmethod
    def _get_service_principal_assigned_roles_endpoint(client_id) -> str:
        return f"https://graph.microsoft.com/v1.0/serviceprincipals/{client_id}/appRoleAssignedTo?$select=appRoleId,principalId,principalType"

    @staticmethod
    def _get_batch_endpoint() -> str:
        return "https://graph.microsoft.com/v1.0/$batch"

    @staticmethod
    def _get_users_endpoint(user_object_id) -> str:
        return "/users/" + user_object_id + "?$select=mail,id"

    @staticmethod
    def _get_group_members_endpoint(group_object_id) -> str:
        return "/groups/" + group_object_id + "/transitiveMembers?$select=mail,id"

    def _get_app_sp_graph_data(self, client_id: str) -> dict:
        msgraph_token = self._get_msgraph_token()
        sp_endpoint = self._get_service_principal_endpoint(client_id)
        graph_data = requests.get(sp_endpoint, headers=self._get_auth_header(msgraph_token)).json()
        return graph_data

    def _get_user_role_assignments(self, client_id, msgraph_token):
        sp_roles_endpoint = self._get_service_principal_assigned_roles_endpoint(client_id)
        return requests.get(sp_roles_endpoint, headers=self._get_auth_header(msgraph_token)).json()

    def _get_user_emails(self, roles_graph_data, msgraph_token):
        batch_endpoint = self._get_batch_endpoint()
        batch_request_body = self._get_batch_users_by_role_assignments_body(roles_graph_data)
        headers = self._get_auth_header(msgraph_token)
        headers["Content-type"] = "application/json"
        max_number_request = 20
        requests_from_batch = batch_request_body["requests"]
        # We split the original batch request body in sub-lits with at most max_number_request elements
        batch_request_body_list = [requests_from_batch[i:i + max_number_request] for i in range(0, len(requests_from_batch), max_number_request)]
        users_graph_data = {"responses": []}

        # For each sub-list it's required to call the batch endpoint for retrieveing user/group information
        for request_body_element in batch_request_body_list:
            batch_request_body_tmp = {"requests": request_body_element}
            users_graph_data_tmp = requests.post(batch_endpoint, json=batch_request_body_tmp, headers=headers).json()
            users_graph_data["responses"] = users_graph_data["responses"] + users_graph_data_tmp["responses"]
        
        return users_graph_data

    def _get_user_emails_from_response(self, users_graph_data):
        user_emails = {}
        for user_data in users_graph_data["responses"]:
            # Handle user endpoint response
            if "users" in user_data["body"]["@odata.context"] and user_data["body"]["mail"] is not None:
                user_emails[user_data["body"]["id"]] = [user_data["body"]["mail"]]
            # Handle group endpoint response
            if "directoryObjects" in user_data["body"]["@odata.context"]:
                group_members_emails = []
                for group_member in user_data["body"]["value"]:
                    if group_member["mail"] is not None and group_member["mail"] not in group_members_emails:
                        group_members_emails.append(group_member["mail"])
                user_emails[user_data["id"]] = group_members_emails
        return user_emails

    def get_workspace_role_assignment_details(self, workspace: Workspace):
        msgraph_token = self._get_msgraph_token()
        app_role_ids = {role_name: workspace.properties[role_id] for role_name, role_id in self.WORKSPACE_ROLES_DICT.items()}
        inverted_app_role_ids = {role_id: role_name for role_name, role_id in app_role_ids.items()}

        sp_id = workspace.properties["sp_id"]
        roles_graph_data = self._get_user_role_assignments(sp_id, msgraph_token)
        users_graph_data = self._get_user_emails(roles_graph_data, msgraph_token)
        user_emails = self._get_user_emails_from_response(users_graph_data)

        workspace_role_assignments_details = defaultdict(list)
        for role_assignment in roles_graph_data["value"]:
            principal_id = role_assignment["principalId"]
            principal_type = role_assignment["principalType"]

            if principal_type != "ServicePrincipal" and principal_id in user_emails:
                app_role_id = role_assignment["appRoleId"]
                app_role_name = inverted_app_role_ids.get(app_role_id)

                if app_role_name:
                    workspace_role_assignments_details[app_role_name].extend(user_emails[principal_id])

        return workspace_role_assignments_details

    def _get_batch_users_by_role_assignments_body(self, roles_graph_data):
        request_body = {"requests": []}
        met_principal_ids = set()
        for role_assignment in roles_graph_data['value']:
            if role_assignment["principalId"] not in met_principal_ids:
                batch_url = ""
                if role_assignment["principalType"] == "User":
                    batch_url = self._get_users_endpoint(role_assignment["principalId"])
                elif role_assignment["principalType"] == "Group":
                    batch_url = self._get_group_members_endpoint(role_assignment["principalId"])
                else:
                    continue
                request_body["requests"].append(
                    {"method": "GET",
                        "url": batch_url,
                        "id": role_assignment["principalId"]})
                met_principal_ids.add(role_assignment["principalId"])

        return request_body

    # This method is called when you create a workspace and you already have an AAD App Registration
    # to link it to. You pass in the client_id and go and get the extra information you need from AAD
    # If the auth_type is `Automatic`, then these values will be written by Terraform.
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

    def _ms_graph_query(self, url: str, http_method: str, json=None) -> dict:
        msgraph_token = self._get_msgraph_token()
        auth_headers = self._get_auth_header(msgraph_token)
        graph_data = {}
        while True:
            if not url:
                break
            logging.debug(f"Making request to: {url}")
            if json:
                response = requests.request(method=http_method, url=url, json=json, headers=auth_headers)
            else:
                response = requests.request(method=http_method, url=url, headers=auth_headers)
            url = ""
            if response.status_code == 200:
                json_response = response.json()
                graph_data = merge_dict(graph_data, json_response)
                if '@odata.nextLink' in json_response:
                    url = json_response['@odata.nextLink']
            else:
                logging.error(f"MS Graph query to: {url} failed with status code {response.status_code}")
                logging.error(f"Full response: {response}")
        return graph_data

    def _get_role_assignment_graph_data_for_user(self, user_id: str) -> dict:
        user_endpoint = f"https://graph.microsoft.com/v1.0/users/{user_id}/appRoleAssignments"
        graph_data = self._ms_graph_query(user_endpoint, "GET")
        return graph_data

    def _get_role_assignment_graph_data_for_service_principal(self, principal_id: str) -> dict:
        svc_principal_endpoint = f"https://graph.microsoft.com/v1.0/servicePrincipals/{principal_id}/appRoleAssignments"
        graph_data = self._ms_graph_query(svc_principal_endpoint, "GET")
        return graph_data

    def _get_identity_type(self, id: str) -> str:
        objects_endpoint = "https://graph.microsoft.com/v1.0/directoryObjects/getByIds"
        request_body = {"ids": [id], "types": ["user", "servicePrincipal"]}
        graph_data = self._ms_graph_query(objects_endpoint, "POST", json=request_body)

        logging.debug(graph_data)

        if "value" not in graph_data or len(graph_data["value"]) != 1:
            logging.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_ACCOUNT_TYPE} {id}")

        object_info = graph_data["value"][0]
        if "@odata.type" not in object_info:
            logging.debug(object_info)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_ACCOUNT_TYPE} {id}")

        return object_info["@odata.type"]

    def extract_workspace_auth_information(self, data: dict) -> dict:
        if ("auth_type" not in data) or (data["auth_type"] != "Automatic" and "client_id" not in data):
            raise AuthConfigValidationError(strings.ACCESS_PLEASE_SUPPLY_CLIENT_ID)

        auth_info = {}
        # The user may want us to create the AAD workspace app and therefore they
        # don't know the client_id yet.
        if data["auth_type"] != "Automatic":
            auth_info = self._get_app_auth_info(data["client_id"])

            # Check we've get all our required roles
            for role in self.WORKSPACE_ROLES_DICT.items():
                if role[1] not in auth_info:
                    raise AuthConfigValidationError(f"{strings.ACCESS_APP_IS_MISSING_ROLE} {role[0]}")

        return auth_info

    def get_identity_role_assignments(self, user_id: str) -> List[RoleAssignment]:
        identity_type = self._get_identity_type(user_id)
        if identity_type == "#microsoft.graph.user":
            graph_data = self._get_role_assignment_graph_data_for_user(user_id)
        elif identity_type == "#microsoft.graph.servicePrincipal":
            graph_data = self._get_role_assignment_graph_data_for_service_principal(user_id)
        else:
            raise AuthConfigValidationError(f"{strings.ACCESS_UNHANDLED_ACCOUNT_TYPE} {identity_type}")

        if 'value' not in graph_data:
            logging.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER} {user_id}")

        logging.debug(graph_data)

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
        if RoleAssignment(resource_id=workspace_sp_id, role_id=workspace.properties['app_role_id_workspace_airlock_manager']) in user_role_assignments:
            return WorkspaceRole.AirlockManager
        return WorkspaceRole.NoRole


def merge_dict(d1, d2):
    dd = defaultdict(list)

    for d in (d1, d2):
        for key, value in d.items():
            if isinstance(value, list):
                dd[key].extend(value)
            else:
                dd[key].append(value)
    return dict(dd)
