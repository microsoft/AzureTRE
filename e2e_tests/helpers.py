import asyncio
import functools
from typing import List, Optional
from contextlib import asynccontextmanager
from httpx import AsyncClient, Timeout, Response
import httpx
import logging
from starlette import status
from azure.identity import ClientSecretCredential, UsernamePasswordCredential

import config
from e2e_tests import cloud

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)

azlogger = logging.getLogger("azure")
azlogger.setLevel(logging.WARN)

GRAPH_TIMEOUT = Timeout(10, read=30)
_AUTOMATION_ADMIN_OBJECT_ID: Optional[str] = None
ROLE_ASSIGNMENT_MAX_ATTEMPTS = 30
ROLE_ASSIGNMENT_SLEEP_SECONDS = 10


class InstallFailedException(Exception):
    pass


def read_workspace_id() -> str:
    with open('workspace_id.txt', 'r') as f:
        workspace_id = f.readline()
    return workspace_id


def write_workspace_id(workspace_id: str) -> None:
    with open('workspace_id.txt', 'w') as f:
        f.write(workspace_id)


def get_auth_header(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}


def get_full_endpoint(endpoint: str) -> str:
    return f"{config.TRE_URL}{endpoint}"


@asynccontextmanager
async def get_template(template_name, endpoint, token, verify):
    async with AsyncClient(verify=verify) as client:
        auth_headers = get_auth_header(token)
        full_endpoint = get_full_endpoint(endpoint)

        response = await client.get(f"{full_endpoint}/{template_name}", headers=auth_headers, timeout=TIMEOUT)
        yield response


async def get_shared_service_by_name(template_name: str, verify, token) -> Optional[dict]:
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        full_endpoint = get_full_endpoint('/api/shared-services')
        auth_headers = get_auth_header(token)

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        assert_status(response, [status.HTTP_200_OK], "Failed to get shared services")
        LOGGER.info(f'RESPONSE: {response}')

        shared_service_list = response.json()["sharedServices"]

        # sort the list by most recently updated and pick the first one
        shared_service_list.sort(reverse=True, key=lambda s: s['updatedWhen'])
        matching_shared_service = None
        for service in shared_service_list:
            if service["templateName"] == template_name:
                matching_shared_service = service
                break

        return matching_shared_service


async def check_aad_auth_redirect(endpoint, verify) -> None:
    LOGGER.info(f"Checking AAD AuthN redirect on: {endpoint}")

    terminal_http_status = [status.HTTP_200_OK,
                            status.HTTP_401_UNAUTHORIZED,
                            status.HTTP_403_FORBIDDEN,
                            status.HTTP_302_FOUND
                            ]

    async with AsyncClient(verify=verify) as client:
        while (True):
            try:
                response = await client.get(url=endpoint, timeout=TIMEOUT)
                LOGGER.info(f"Endpoint Response: {endpoint} {response}")

                if response.status_code in terminal_http_status:
                    break

                await asyncio.sleep(30)

            except Exception:
                LOGGER.exception("Generic execption in http request.")

        assert_status(response, [status.HTTP_302_FOUND])
        assert response.has_redirect_location

        location = response.headers["Location"]
        LOGGER.info(f"Returned redirect URL: {location}")

        valid_redirection_contains = ["login", "microsoftonline", "oauth2", "authorize"]
        assert all(word in location for word in valid_redirection_contains), "Redirect URL doesn't apper to be valid"


async def get_admin_token(verify) -> str:
    scope_uri = f"api://{config.API_CLIENT_ID}"
    return get_token(scope_uri, verify)


def get_token(scope_uri, verify) -> str:
    if config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != "":
        # Logging in as an Enterprise Application: Use Client Credentials flow
        credential = ClientSecretCredential(config.AAD_TENANT_ID, config.TEST_ACCOUNT_CLIENT_ID, config.TEST_ACCOUNT_CLIENT_SECRET, connection_verify=verify, authority=cloud.get_aad_authority_fqdn())
        token = credential.get_token(f'{scope_uri}/.default')
    else:
        # Logging in as a User: Use Resource Owner Password Credentials flow
        credential = UsernamePasswordCredential(config.TEST_APP_ID, config.TEST_USER_NAME, config.TEST_USER_PASSWORD, connection_verify=verify, authority=cloud.get_aad_authority_fqdn(), tenant_id=config.AAD_TENANT_ID)
        token = credential.get_token(f'{scope_uri}/user_impersonation')

    return token.token


def assert_status(response: Response, expected_status: List[int] = [200], message_prefix: str = "Unexpected HTTP Status"):
    assert response.status_code in expected_status, \
        f"{message_prefix}. Expected: {expected_status}. Actual: {response.status_code}. Response text: {response.text}"


async def ensure_automation_admin_has_airlock_role(workspace_id: str, admin_token: str, verify: bool) -> None:
    await _ensure_automation_admin_has_role(workspace_id, admin_token, verify, role_name="Airlock Manager")


async def ensure_automation_admin_has_workspace_owner_role(workspace_id: str, admin_token: str, verify: bool) -> None:
    await _ensure_automation_admin_has_role(workspace_id, admin_token, verify, role_name="WorkspaceOwner")


async def _ensure_automation_admin_has_role(workspace_id: str, admin_token: str, verify: bool, role_name: str) -> None:
    """Assign the automation admin identity to a workspace role via the TRE API."""
    if workspace_id == "":
        LOGGER.info("Workspace ID missing; skipping %s assignment", role_name)
        return

    if config.TEST_ACCOUNT_CLIENT_ID == "" and config.TEST_USER_NAME == "":
        LOGGER.info("No automation admin identity configured; skipping %s assignment", role_name)
        return

    if not await _wait_for_user_management_configuration(workspace_id, admin_token, verify, role_name):
        return

    role_id = await _get_workspace_role_id(workspace_id, admin_token, verify, role_name=role_name)
    if role_id is None:
        LOGGER.warning("%s role not found for workspace %s; skipping assignment", role_name, workspace_id)
        return

    user_object_id = await _get_automation_admin_object_id(workspace_id, admin_token, verify)
    if user_object_id is None:
        LOGGER.warning("Unable to determine automation admin directory object id; skipping %s assignment", role_name)
        return

    await _assign_workspace_role_via_api(workspace_id, role_id, user_object_id, admin_token, verify, role_name)


async def _get_workspace_role_id(workspace_id: str, admin_token: str, verify: bool, role_name: str) -> Optional[str]:
    """Retrieve a workspace role ID, retrying on 404 to allow time for Entra ID role propagation."""
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        headers = get_auth_header(admin_token)
        
        for attempt in range(ROLE_ASSIGNMENT_MAX_ATTEMPTS):
            response = await client.get(get_full_endpoint(f"/api/workspaces/{workspace_id}/roles"), headers=headers, timeout=TIMEOUT)
            
            if response.status_code == status.HTTP_404_NOT_FOUND:
                LOGGER.info("Workspace roles not yet available for %s (%s/%s)", workspace_id, attempt + 1, ROLE_ASSIGNMENT_MAX_ATTEMPTS)
                await asyncio.sleep(ROLE_ASSIGNMENT_SLEEP_SECONDS)
                continue
            
            assert_status(response, [status.HTTP_200_OK], f"Failed to get workspace roles for {workspace_id}")
            
            for role in response.json().get("roles", []):
                if role.get("displayName") == role_name:
                    return role.get("id")
            
            return None
        
        LOGGER.warning("Workspace roles never became available for %s after %s attempts", workspace_id, ROLE_ASSIGNMENT_MAX_ATTEMPTS)
        return None


async def _assign_workspace_role_via_api(workspace_id: str, role_id: str, user_id: str, admin_token: str, verify: bool, role_name: str) -> None:
    payload = {
        "role_id": role_id,
        "user_ids": [user_id]
    }

    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        headers = get_auth_header(admin_token)
        response = await client.post(
            get_full_endpoint(f"/api/workspaces/{workspace_id}/users/assign"),
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        assert_status(response, [status.HTTP_202_ACCEPTED], f"Failed to assign {role_name} role for workspace {workspace_id}")


async def _get_automation_admin_object_id(workspace_id: str, admin_token: str, verify: bool) -> Optional[str]:
    global _AUTOMATION_ADMIN_OBJECT_ID
    if _AUTOMATION_ADMIN_OBJECT_ID:
        return _AUTOMATION_ADMIN_OBJECT_ID

    if config.TEST_USER_NAME != "":
        user_id = await _get_assignable_user_id(workspace_id, admin_token, verify, config.TEST_USER_NAME)
        if user_id:
            _AUTOMATION_ADMIN_OBJECT_ID = user_id
            return user_id
        LOGGER.warning("Assignable user lookup failed for %s; falling back to Graph", config.TEST_USER_NAME)

    loop = asyncio.get_running_loop()
    directory_id = await loop.run_in_executor(None, functools.partial(_get_directory_object_id_via_graph, verify))
    if directory_id:
        _AUTOMATION_ADMIN_OBJECT_ID = directory_id
    return directory_id


async def _get_assignable_user_id(workspace_id: str, admin_token: str, verify: bool, user_principal_name: str) -> Optional[str]:
    params = {
        "filter": user_principal_name,
        "maxResultCount": 50
    }

    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        headers = get_auth_header(admin_token)
        response = await client.get(
            get_full_endpoint(f"/api/workspaces/{workspace_id}/assignable-users"),
            headers=headers,
            params=params,
            timeout=TIMEOUT
        )
        assert_status(response, [status.HTTP_200_OK], f"Failed to get assignable users for workspace {workspace_id}")

        for user in response.json().get("assignableUsers", []):
            upn = user.get("userPrincipalName", "").lower()
            if upn == user_principal_name.lower():
                return user.get("id")

    return None


async def _wait_for_user_management_configuration(workspace_id: str, admin_token: str, verify: bool, role_name: str) -> bool:
    """Poll the workspace until Entra ID role/group data is available."""
    for attempt in range(ROLE_ASSIGNMENT_MAX_ATTEMPTS):
        workspace = await _get_workspace_details(workspace_id, admin_token, verify)
        if _workspace_supports_user_management(workspace):
            return True

        if _workspace_cannot_support_user_management(workspace):
            LOGGER.warning("Workspace %s does not support user management; skipping %s assignment", workspace_id, role_name)
            return False

        LOGGER.info("Waiting for workspace %s user management config (%s/%s)", workspace_id, attempt + 1, ROLE_ASSIGNMENT_MAX_ATTEMPTS)
        await asyncio.sleep(ROLE_ASSIGNMENT_SLEEP_SECONDS)

    LOGGER.warning("Workspace %s never exposed user management config; skipping %s assignment", workspace_id, role_name)
    return False


async def _get_workspace_details(workspace_id: str, admin_token: str, verify: bool) -> dict:
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        headers = get_auth_header(admin_token)
        response = await client.get(get_full_endpoint(f"/api/workspaces/{workspace_id}"), headers=headers, timeout=TIMEOUT)
        assert_status(response, [status.HTTP_200_OK], f"Failed to get workspace {workspace_id}")
        return response.json().get("workspace", {})


def _workspace_supports_user_management(workspace: dict) -> bool:
    props = workspace.get("properties", {})
    has_groups = props.get("create_aad_groups") is True
    required_fields = [
        "sp_id",
        "app_role_id_workspace_owner",
        "app_role_id_workspace_researcher",
        "app_role_id_workspace_airlock_manager"
    ]
    return has_groups and all(field in props for field in required_fields)


def _workspace_cannot_support_user_management(workspace: dict) -> bool:
    props = workspace.get("properties", {})
    deployment_status = workspace.get("deploymentStatus", "")
    groups_flag = props.get("create_aad_groups")
    return deployment_status == "deployed" and not groups_flag


def _get_directory_object_id_via_graph(verify: bool) -> Optional[str]:
    graph_resource = cloud.get_ms_graph_resource()
    graph_base_url = f"{graph_resource}/v1.0"
    token = get_token(graph_resource, verify)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    identity_id: Optional[str] = None
    with httpx.Client(headers=headers, timeout=GRAPH_TIMEOUT, verify=verify) as client:
        if config.TEST_ACCOUNT_CLIENT_ID != "":
            identity_id = _get_service_principal_id(client, graph_base_url, config.TEST_ACCOUNT_CLIENT_ID)
        elif config.TEST_USER_NAME != "":
            identity_id = _get_user_object_id(client, graph_base_url, config.TEST_USER_NAME)

    return identity_id


def _get_service_principal_id(client: httpx.Client, base_url: str, app_id: str) -> Optional[str]:
    resp = client.get(f"{base_url}/servicePrincipals", params={"$filter": f"appId eq '{app_id}'"})
    resp.raise_for_status()
    values = resp.json().get("value", [])
    if not values:
        return None
    return values[0]["id"]


def _get_user_object_id(client: httpx.Client, base_url: str, user_principal_name: str) -> Optional[str]:
    if user_principal_name == "":
        return None

    resp = client.get(f"{base_url}/users/{user_principal_name}", params={"$select": "id"})
    if resp.status_code == status.HTTP_404_NOT_FOUND:
        return None

    resp.raise_for_status()
    return resp.json().get("id")
