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
    """Retrieve a workspace role ID, retrying on 404/500/503 to allow time for Entra ID role propagation."""
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        headers = get_auth_header(admin_token)

        for attempt in range(ROLE_ASSIGNMENT_MAX_ATTEMPTS):
            response = await client.get(get_full_endpoint(f"/api/workspaces/{workspace_id}/roles"), headers=headers, timeout=TIMEOUT)

            if response.status_code == status.HTTP_404_NOT_FOUND:
                LOGGER.info("Workspace roles not yet available for %s (%s/%s)", workspace_id, attempt + 1, ROLE_ASSIGNMENT_MAX_ATTEMPTS)
                await asyncio.sleep(ROLE_ASSIGNMENT_SLEEP_SECONDS)
                continue

            if response.status_code in (status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_503_SERVICE_UNAVAILABLE):
                LOGGER.info("Workspace roles endpoint returned %s for %s, likely Entra ID propagation delay (%s/%s)", response.status_code, workspace_id, attempt + 1, ROLE_ASSIGNMENT_MAX_ATTEMPTS)
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
    """
    Assign a user/service principal directly to an app role via Graph API.
    This bypasses group membership and uses direct app role assignment,
    which propagates to tokens immediately without the 5-15 minute delay
    that group membership changes require.
    """
    # Get workspace details to get the sp_id (resource service principal)
    workspace = await _get_workspace_details(workspace_id, admin_token, verify)
    sp_id = workspace.get("properties", {}).get("sp_id")
    if not sp_id:
        LOGGER.error("Workspace %s has no sp_id; cannot assign role directly", workspace_id)
        return

    # Do direct Graph API call to assign the principal to the app role
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(
        None,
        functools.partial(_assign_principal_to_app_role_via_graph, user_id, sp_id, role_id, verify)
    )

    if success:
        LOGGER.info("Direct app role assignment succeeded for %s role in workspace %s", role_name, workspace_id)
    else:
        LOGGER.warning("Direct app role assignment failed for %s role in workspace %s", role_name, workspace_id)

    # Brief wait for token refresh - direct assignments should be immediate but give it a moment
    await asyncio.sleep(5)


def _get_application_admin_graph_token(verify: bool) -> Optional[str]:
    """
    Get a Graph API token using Application Admin credentials.
    The Application Admin has Application.ReadWrite.OwnedBy permission and is the owner
    of workspace service principals, allowing it to manage app role assignments.
    """
    if config.APPLICATION_ADMIN_CLIENT_ID == "" or config.APPLICATION_ADMIN_CLIENT_SECRET == "":
        LOGGER.warning("Application Admin credentials not configured")
        return None

    try:
        graph_resource = cloud.get_ms_graph_resource()
        credential = ClientSecretCredential(
            config.AAD_TENANT_ID,
            config.APPLICATION_ADMIN_CLIENT_ID,
            config.APPLICATION_ADMIN_CLIENT_SECRET,
            connection_verify=verify,
            authority=cloud.get_aad_authority_fqdn()
        )
        token = credential.get_token(f'{graph_resource}/.default')
        return token.token
    except Exception as e:
        LOGGER.error("Failed to get Application Admin token: %s", e)
        return None


def _assign_principal_to_app_role_via_graph(principal_id: str, resource_id: str, app_role_id: str, verify: bool) -> bool:
    """
    Assign a user or service principal directly to an app role on a resource via Graph API.
    Direct app role assignments propagate to tokens immediately, unlike group membership.

    Uses the Application Admin credentials since it owns the workspace service principals
    and has Application.ReadWrite.OwnedBy permission.
    """
    graph_resource = cloud.get_ms_graph_resource()
    graph_base_url = f"{graph_resource}/v1.0"

    # Use Application Admin credentials - it owns workspace SPs and can manage their role assignments
    token = _get_application_admin_graph_token(verify)
    if not token:
        LOGGER.warning("Could not get Application Admin token, falling back to automation admin")
        token = get_token(graph_resource, verify)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    with httpx.Client(headers=headers, timeout=GRAPH_TIMEOUT, verify=verify) as client:
        # Use the resource's appRoleAssignedTo endpoint
        # This allows the resource owner to add assignments without special Graph permissions
        url = f"{graph_base_url}/servicePrincipals/{resource_id}/appRoleAssignedTo"

        body = {
            "principalId": principal_id,
            "resourceId": resource_id,
            "appRoleId": app_role_id
        }

        resp = client.post(url, json=body)

        if resp.status_code == 201:
            LOGGER.info("Successfully assigned principal %s directly to app role %s", principal_id, app_role_id)
            return True

        if resp.status_code == 400:
            try:
                error_data = resp.json()
                error_message = error_data.get("error", {}).get("message", "")
                if "already been assigned" in error_message or "already exists" in error_message:
                    LOGGER.info("Principal %s already has app role %s", principal_id, app_role_id)
                    return True
            except Exception:
                pass

        if resp.status_code == 403:
            LOGGER.warning(
                "Direct app role assignment failed with 403 Forbidden. "
                "The automation admin may not be an owner of the workspace service principal. "
                "Ensure the workspace was deployed with workspace_owner_object_id set to the automation admin's object ID. "
                "Response: %s", resp.text
            )
            return False

        LOGGER.error("Graph API call to %s failed with status %s: %s", url, resp.status_code, resp.text)
        return False


async def _get_automation_admin_object_id(workspace_id: str, admin_token: str, verify: bool) -> Optional[str]:
    """Get the directory object ID for the automation admin (user or service principal)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(_get_directory_object_id_via_graph, verify))


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
