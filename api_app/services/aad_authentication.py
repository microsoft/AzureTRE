from collections import defaultdict
from enum import Enum
from typing import List, Optional

import requests
from fastapi import HTTPException, Request, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from msal import ConfidentialClientApplication
from semantic_version import Version

from auth.exceptions import AuthError, TokenExpired, TokenInvalid, TokenSignatureInvalid
from auth.registry import get_core_validator, get_workspace_validator
from core import config
from db.errors import EntityDoesNotExist
from models.domain.authentication import User, RoleAssignment
from models.domain.workspace import Workspace, WorkspaceRole
from models.domain.workspace_users import AssignableUser, AssignedUser, AssignmentType, Role
from resources import strings
from db.repositories.workspaces import WorkspaceRepository
from services.logging import logger


MICROSOFT_GRAPH_URL = config.MICROSOFT_GRAPH_URL.strip("/")
GRAPH_REQUEST_TIMEOUT = 10
USER_MANAGEMENT_MINIMUM_BASE_TEMPLATE_VERSION = "2.1.0"


class AuthConfigValidationError(Exception):
    """Raised when the input auth information is invalid."""


class UserRoleAssignmentError(Exception):
    """Raised when a user role assignment fails."""


def _authenticated_user_to_user(validated) -> User:
    """Convert an :class:`~auth.models.AuthenticatedUser` to the legacy :class:`~models.domain.authentication.User`."""
    return User(
        id=validated.id,
        name=validated.name,
        email=validated.email or "",
        roles=list(validated.roles),
    )


class PrincipalType(Enum):
    User = "User"
    Group = "Group"
    ServicePrincipal = "ServicePrincipal"


class AzureADAuthorization(OAuth2AuthorizationCodeBearer):
    """FastAPI security dependency that validates Entra ID JWTs.

    Uses :mod:`auth.token_validator` (backed by :class:`jwt.PyJWKClient`) for
    JWT validation so key management is handled automatically.
    """

    require_one_of_roles: Optional[list] = None
    aad_instance: str = config.AAD_AUTHORITY_URL

    TRE_CORE_ROLES = ['TREAdmin', 'TREUser', 'TREAirlockAutomation']
    WORKSPACE_ROLES_DICT = {
        'WorkspaceOwner': 'app_role_id_workspace_owner',
        'WorkspaceResearcher': 'app_role_id_workspace_researcher',
        'AirlockManager': 'app_role_id_workspace_airlock_manager',
    }

    def __init__(self, auto_error: bool = True, require_one_of_roles: Optional[list] = None):
        super().__init__(
            authorizationUrl=f"{self.aad_instance}/{config.AAD_TENANT_ID}/oauth2/v2.0/authorize",
            tokenUrl=f"{self.aad_instance}/{config.AAD_TENANT_ID}/oauth2/v2.0/token",
            refreshUrl=f"{self.aad_instance}/{config.AAD_TENANT_ID}/oauth2/v2.0/token",
            scheme_name="oauth2",
            auto_error=auto_error,
        )
        self.require_one_of_roles = require_one_of_roles

    async def __call__(self, request: Request) -> User:
        token: str = await super().__call__(request)

        decoded_user = None

        # Try workspace app registration first when a workspace_id is present
        # and the route requires workspace-scoped roles.
        if 'workspace_id' in request.path_params and any(
            role in self.require_one_of_roles for role in self.WORKSPACE_ROLES_DICT
        ):
            logger.debug("Workspace ID present — attempting workspace app registration")
            try:
                app_reg_id = await self._fetch_ws_app_reg_id_from_ws_id(request)
                if app_reg_id:
                    try:
                        validated = get_workspace_validator(app_reg_id).validate(token)
                        decoded_user = self._get_user_from_token(validated)
                    except (TokenExpired, TokenSignatureInvalid) as exc:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=strings.EXPIRED_SIGNATURE
                            if isinstance(exc, TokenExpired)
                            else strings.INVALID_SIGNATURE,
                        )
                    except TokenInvalid:
                        logger.debug(
                            "Workspace token invalid, will try core app registration"
                        )
            except HTTPException:
                raise
            except Exception as exc:
                logger.debug("Failed to resolve workspace app registration: %s", exc)

        # Try core app registration for TRE core roles.
        if decoded_user is None and any(
            role in self.require_one_of_roles for role in self.TRE_CORE_ROLES
        ):
            try:
                validated = get_core_validator().validate(token)
                decoded_user = self._get_user_from_token(validated)
            except TokenExpired:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=strings.EXPIRED_SIGNATURE,
                )
            except TokenSignatureInvalid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=strings.INVALID_SIGNATURE,
                )
            except TokenInvalid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=strings.INVALID_TOKEN,
                )
            except AuthError as exc:
                logger.debug("Core token validation failed: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=strings.AUTH_UNABLE_TO_VALIDATE_TOKEN,
                )

        if decoded_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=strings.AUTH_UNABLE_TO_VALIDATE_TOKEN,
            )

        if not any(role in self.require_one_of_roles for role in decoded_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {self.require_one_of_roles}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return decoded_user

    @staticmethod
    async def _fetch_ws_app_reg_id_from_ws_id(request: Request) -> str:
        workspace_id = request.path_params.get('workspace_id')
        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS,
            )
        try:
            ws_repo = await WorkspaceRepository.create()
            workspace = await ws_repo.get_workspace_by_id(workspace_id)
            return workspace.properties.get('client_id', '')
        except EntityDoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=strings.WORKSPACE_DOES_NOT_EXIST,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to get workspace app registration ID for workspace %s",
                workspace_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=strings.AUTH_COULD_NOT_VALIDATE_CREDENTIALS,
            ) from exc


    @staticmethod
    def _get_user_from_token(validated) -> User:
        """Convert a validated :class:`~auth.models.AuthenticatedUser` to a :class:`User`.

        This method is kept as an instance-patchable hook so tests can inject
        specific users without needing real JWTs.
        """
        return _authenticated_user_to_user(validated)

    @staticmethod
    def _get_msgraph_token() -> str:
        scopes = [f"{MICROSOFT_GRAPH_URL}/.default"]
        app = ConfidentialClientApplication(client_id=config.API_CLIENT_ID, client_credential=config.API_CLIENT_SECRET, authority=f"{config.AAD_AUTHORITY_URL}/{config.AAD_TENANT_ID}")
        try:
            result = app.acquire_token_silent(scopes=scopes, account=None)
        except Exception:
            result = None
        if not result:
            logger.debug('No suitable token exists in cache, getting a new one from AAD')
            result = app.acquire_token_for_client(scopes=scopes)
        if "access_token" not in result:
            raise Exception(f"API app registration access token cannot be retrieved. {result.get('error')}: {result.get('error_description')}")
        return result["access_token"]

    @staticmethod
    def _get_auth_header(msgraph_token: str) -> dict:
        return {'Authorization': 'Bearer ' + msgraph_token}

    @staticmethod
    def _get_service_principal_endpoint(client_id) -> str:
        return f"{MICROSOFT_GRAPH_URL}/v1.0/serviceprincipals?$filter=appid eq '{client_id}'"

    @staticmethod
    def _get_service_principal_assigned_roles_endpoint(client_id) -> str:
        return f"{MICROSOFT_GRAPH_URL}/v1.0/serviceprincipals/{client_id}/appRoleAssignedTo?$select=appRoleId,principalId,principalType,principalDisplayName"

    @staticmethod
    def _get_batch_endpoint() -> str:
        return f"{MICROSOFT_GRAPH_URL}/v1.0/$batch"

    @staticmethod
    def _get_users_endpoint(user_object_id) -> str:
        return "/users/" + user_object_id + "?$select=displayName,mail,id,userPrincipalName"

    @staticmethod
    def _get_group_members_endpoint(group_object_id) -> str:
        return "/groups/" + group_object_id + "/transitiveMembers?$select=displayName,mail,id,userPrincipalName"

    def _get_app_sp_graph_data(self, client_id: str) -> dict:
        sp_endpoint = self._get_service_principal_endpoint(client_id)
        graph_data = self._ms_graph_query(sp_endpoint, "GET")
        return graph_data

    def _get_user_role_assignments(self, client_id):
        sp_roles_endpoint = self._get_service_principal_assigned_roles_endpoint(client_id)
        return self._ms_graph_query(sp_roles_endpoint, "GET")

    def _get_user_details(self, roles_graph_data, msgraph_token):
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
            users_graph_data_tmp = requests.post(batch_endpoint, json=batch_request_body_tmp, headers=headers, timeout=GRAPH_REQUEST_TIMEOUT).json()
            users_graph_data["responses"] = users_graph_data["responses"] + users_graph_data_tmp["responses"]

        return users_graph_data

    def _get_roles_for_principal(self, user_id, roles_graph_data, app_id_to_role_name) -> List[Role]:
        roles = []
        for role_assignment in roles_graph_data["value"]:
            if role_assignment["principalId"] == user_id:
                roles.append(Role(id=role_assignment["appRoleId"], displayName=app_id_to_role_name[role_assignment["appRoleId"]]))
        return roles

    def _get_users_inc_groups_from_response(self, users_graph_data, roles_graph_data, app_id_to_role_name) -> List[AssignedUser]:
        users = []
        for user_data in users_graph_data["responses"]:
            if "users" in user_data["body"]["@odata.context"]:
                # Handle user endpoint response
                user_id = user_data["body"]["id"]
                user_name = user_data["body"]["displayName"]

                if "users" in user_data["body"]["@odata.context"]:
                    user_principal_name = user_data["body"]["userPrincipalName"]
                    user_email = user_data["body"]["mail"]
                    # if user with id does not already exist in users
                    user_roles = self._get_roles_for_principal(user_id, roles_graph_data, app_id_to_role_name)

                    if not any(user.id == user_id for user in users):
                        users.append(AssignedUser(id=user_id, displayName=user_name, userPrincipalName=user_principal_name, email=user_email, roles=user_roles))
                    else:
                        user = next((user for user in users if user.id == user_id), None)
                        user.roles = list(set(user.roles + user_roles))

            # Handle group endpoint response
            elif "directoryObjects" in user_data["body"]["@odata.context"]:
                group_id = user_data["id"]
                for group_member in user_data["body"]["value"]:
                    user_id = group_member["id"]
                    user_name = group_member["displayName"]
                    user_principal_name = group_member["userPrincipalName"]
                    user_email = group_member["mail"]

                    group_roles = self._get_roles_for_principal(group_id, roles_graph_data, app_id_to_role_name)

                    if not any(user.id == user_id for user in users):
                        users.append(AssignedUser(id=user_id, displayName=user_name, userPrincipalName=user_principal_name, email=user_email, roles=group_roles))
                    else:
                        user = next((user for user in users if user.id == user_id), None)
                        user.roles = list(set(user.roles + group_roles))

        return users

    def get_workspace_users(self, workspace: Workspace) -> List[AssignedUser]:
        msgraph_token = self._get_msgraph_token()
        sp_graph_data = self._get_app_sp_graph_data(workspace.properties["client_id"])
        app_id_to_role_name = {app_role["id"]: (app_role["value"]) for app_role in sp_graph_data["value"][0]["appRoles"]}
        roles_graph_data = self._get_user_role_assignments(workspace.properties["sp_id"])
        users_graph_data = self._get_user_details(roles_graph_data, msgraph_token)
        users_inc_groups = self._get_users_inc_groups_from_response(users_graph_data, roles_graph_data, app_id_to_role_name)

        return users_inc_groups

    def get_workspace_user_emails_by_role_assignment(self, workspace: Workspace):
        users = self.get_workspace_users(workspace)
        workspace_role_assignments_details = {}
        for user in users:
            if user.email:
                for role in user.roles:
                    if role.displayName not in workspace_role_assignments_details:
                        workspace_role_assignments_details[role.displayName] = []
                    workspace_role_assignments_details[role.displayName].append(user.email)
        return workspace_role_assignments_details

    def get_assignable_users(self, filter: str = "", maxResultCount: int = 5) -> List[AssignableUser]:
        users_endpoint = f"{MICROSOFT_GRAPH_URL}/v1.0/users?$filter=startswith(displayName,'{filter}')&$top={maxResultCount}"
        graph_data = self._ms_graph_query(users_endpoint, "GET")
        result = []

        for user_data in graph_data["value"]:
            result.append(
                AssignableUser(id=user_data["id"], displayName=user_data["displayName"], userPrincipalName=user_data["userPrincipalName"], email=user_data["mail"])
            )

        return result

    def get_workspace_roles(self, workspace: Workspace) -> List[Role]:
        app_roles_endpoint = f"{MICROSOFT_GRAPH_URL}/v1.0/servicePrincipals/{workspace.properties['sp_id']}/appRoles"
        graph_data = self._ms_graph_query(app_roles_endpoint, "GET")

        roles = []

        roleAssignmentType = AssignmentType.APP_ROLE
        if self._is_workspace_role_group_in_use(workspace):
            roleAssignmentType = AssignmentType.GROUP

        for role in graph_data["value"]:
            roles.append(Role(id=role["id"],
                              displayName=role["displayName"],
                              type=roleAssignmentType))

        return roles

    def assign_workspace_user(self, user_id: str, workspace: Workspace, role_id: str) -> None:
        # User already has the role, do nothing
        if self._is_user_in_role(user_id, role_id):
            return
        if compare_versions(workspace.templateVersion, USER_MANAGEMENT_MINIMUM_BASE_TEMPLATE_VERSION) < 0:
            logger.error(f"Unable to assign user {user_id} to group with role {role_id}, Workspace needs to be version 2.2.0 or greater")
            raise UserRoleAssignmentError(f"Unable to assign user {user_id} to group with role {role_id}, Workspace needs to be version 2.2.0 or greater")
        if not self._is_workspace_role_group_in_use(workspace):
            logger.error(f"Unable to assign user {user_id} to group with role {role_id}, Entra ID groups are not in use on this workspace")
            raise UserRoleAssignmentError(f"Unable to assign user {user_id} to group with role {role_id}, Entra ID groups are not in use on this workspace")
        return self._assign_workspace_user_to_application_group(user_id, workspace, role_id)

    def _is_user_in_role(self, user_id: str, role_id: str) -> bool:
        user_app_role_query = f"{MICROSOFT_GRAPH_URL}/v1.0/users/{user_id}/appRoleAssignments"
        user_app_roles = self._ms_graph_query(user_app_role_query, "GET")
        return any(r for r in user_app_roles["value"] if r["appRoleId"] == role_id)

    def _is_workspace_role_group_in_use(self, workspace: Workspace) -> bool:
        aad_groups_in_user = workspace.properties["create_aad_groups"]
        return aad_groups_in_user

    def _get_workspace_group_name(self, workspace: Workspace, role_id: str) -> tuple:
        tre_id = workspace.properties["tre_id"]
        workspace_id = workspace.properties["workspace_id"]
        group_name = ""
        app_role_id_suffix = ""
        if workspace.properties["app_role_id_workspace_researcher"] == role_id:
            group_name = "Workspace Researchers"
            app_role_id_suffix = "workspace_researcher"
        elif workspace.properties["app_role_id_workspace_owner"] == role_id:
            group_name = "Workspace Owners"
            app_role_id_suffix = "workspace_owner"
        elif workspace.properties["app_role_id_workspace_airlock_manager"] == role_id:
            group_name = "Airlock Managers"
            app_role_id_suffix = "workspace_airlock_manager"
        else:
            raise UserRoleAssignmentError(f"Unknown role: {role_id}")

        return (f"{tre_id}-ws-{workspace_id} {group_name}", f"app_role_id_{app_role_id_suffix}")

    def _assign_workspace_user_to_application_group(self, user_id: str, workspace: Workspace, role_id: str):
        roles_graph_data = self._get_user_role_assignments(workspace.properties["sp_id"])
        group_details = self._get_workspace_group_name(workspace, role_id)
        group_name = group_details[0]
        workspace_app_role_field = group_details[1]

        for group in [item for item in roles_graph_data["value"] if item["principalType"] == PrincipalType.Group.value]:
            if group.get("principalDisplayName") == group_name and group.get("appRoleId") == workspace.properties[workspace_app_role_field]:
                self._add_user_to_group(user_id, group["principalId"])
                return

        raise UserRoleAssignmentError(f"Unable to assign user to group with role: {role_id}")

    def _remove_workspace_user_from_application_group(self, user_id: str, workspace: Workspace, role_id: str):
        roles_graph_data = self._get_user_role_assignments(workspace.properties["sp_id"])
        group_details = self._get_workspace_group_name(workspace, role_id)
        group_name = group_details[0]
        workspace_app_role_field = group_details[1]

        for group in [item for item in roles_graph_data["value"] if item["principalType"] == PrincipalType.Group.value]:
            if group.get("principalDisplayName") == group_name and group.get("appRoleId") == workspace.properties[workspace_app_role_field]:
                self._remove_user_from_group(user_id, group["principalId"])
                return
        raise UserRoleAssignmentError(f"Unable to assign user to group with role: {role_id}")

    def _add_user_to_group(self, user_id: str, group_id: str):
        url = f"{MICROSOFT_GRAPH_URL}/v1.0/groups/{group_id}/members/$ref"
        body = {
            "@odata.id": f"{MICROSOFT_GRAPH_URL}/v1.0/users/{user_id}"
        }

        response = self._ms_graph_query(url, "POST", json=body)
        return response

    def _remove_user_from_group(self, user_id: str, group_id: str):
        url = f"{MICROSOFT_GRAPH_URL}/v1.0/groups/{group_id}/members/{user_id}/$ref"

        response = self._ms_graph_query(url, "DELETE")
        return response

    def _get_role_assignment_for_user(self, user_id: str, role_id: str) -> dict:
        user_role_assignments = self._get_role_assignment_graph_data_for_user(user_id)
        for role in user_role_assignments["value"]:
            if role["appRoleId"] == role_id:
                return role

    def remove_workspace_role_user_assignment(self,
                                              user_id: str,
                                              role_id: str,
                                              workspace: Workspace
                                              ) -> None:
        if compare_versions(workspace.templateVersion, USER_MANAGEMENT_MINIMUM_BASE_TEMPLATE_VERSION) < 0:
            logger.error(f"Unable to remove user {user_id} from group with role {role_id}, Workspace needs to be version 2.2.0 or greater")
            raise UserRoleAssignmentError(f"Unable to remove user {user_id} from group with role {role_id}, Workspace needs to be version 2.2.0 or greater")
        if not self._is_workspace_role_group_in_use(workspace):
            logger.error(f"Unable to remove user {user_id} from group with role {role_id}, Entra ID groups are not in use on this workspace")
            raise UserRoleAssignmentError(f"Unable to remove user {user_id} from group with role {role_id}, Entra ID groups are not in use on this workspace")
        return self._remove_workspace_user_from_application_group(user_id, workspace, role_id)

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
            logger.debug(graph_data)
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
            logger.debug(f"Making request to: {url}")
            if json:
                response = requests.request(method=http_method, url=url, json=json, headers=auth_headers, timeout=GRAPH_REQUEST_TIMEOUT)
            else:
                response = requests.request(method=http_method, url=url, headers=auth_headers, timeout=GRAPH_REQUEST_TIMEOUT)
            url = ""
            if response.status_code == 200:
                json_response = response.json()
                graph_data = merge_dict(graph_data, json_response)
                if '@odata.nextLink' in json_response:
                    url = json_response['@odata.nextLink']
            else:
                logger.error(f"MS Graph query to: {url} failed with status code {response.status_code}")
                logger.error(f"Full response: {response}")
        return graph_data

    def _get_role_assignment_graph_data_for_user(self, user_id: str) -> dict:
        user_endpoint = f"{MICROSOFT_GRAPH_URL}/v1.0/users/{user_id}/appRoleAssignments"
        graph_data = self._ms_graph_query(user_endpoint, "GET")
        return graph_data

    def _get_role_assignment_graph_data_for_service_principal(self, principal_id: str) -> dict:
        svc_principal_endpoint = f"{MICROSOFT_GRAPH_URL}/v1.0/servicePrincipals/{principal_id}/appRoleAssignments"
        graph_data = self._ms_graph_query(svc_principal_endpoint, "GET")
        return graph_data

    def _get_identity_type(self, id: str) -> str:
        objects_endpoint = f"{MICROSOFT_GRAPH_URL}/v1.0/directoryObjects/getByIds"
        request_body = {"ids": [id], "types": ["user", "servicePrincipal"]}
        graph_data = self._ms_graph_query(objects_endpoint, "POST", json=request_body)

        logger.debug(graph_data)

        if "value" not in graph_data or len(graph_data["value"]) != 1:
            logger.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_ACCOUNT_TYPE} {id}")

        object_info = graph_data["value"][0]
        if "@odata.type" not in object_info:
            logger.debug(object_info)
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
            logger.debug(graph_data)
            raise AuthConfigValidationError(f"{strings.ACCESS_UNABLE_TO_GET_ROLE_ASSIGNMENTS_FOR_USER} {user_id}")

        logger.debug(graph_data)

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


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings in the format major.minor.build.

    Returns:
         -1 if v1 < v2,
          0 if v1 == v2,
          1 if v1 > v2.
    """
    version1 = Version(v1)
    version2 = Version(v2)
    if version1 < version2:
        return -1
    elif version1 > version2:
        return 1
    else:
        return 0


def merge_dict(d1, d2):
    dd = defaultdict(list)

    for d in (d1, d2):
        for key, value in d.items():
            if isinstance(value, list):
                dd[key].extend(value)
            else:
                dd[key].append(value)
    return dict(dd)
