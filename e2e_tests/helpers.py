import asyncio
import base64
import functools
import json
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

ROLE_ASSIGNMENT_MAX_ATTEMPTS = 30
ROLE_ASSIGNMENT_SLEEP_SECONDS = 10
ROLE_VERIFICATION_MAX_ATTEMPTS = 12
ROLE_VERIFICATION_SLEEP_SECONDS = 5


class InstallFailedException(Exception):
    pass


def _is_service_principal_auth() -> bool:
    """Check if using service principal (client credentials) authentication."""
    return config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != ""


def _has_automation_identity() -> bool:
    """Check if any automation identity (service principal or user) is configured."""
    return config.TEST_ACCOUNT_CLIENT_ID != "" or config.TEST_USER_NAME != ""


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
    if _is_service_principal_auth():
        # Logging in as an Enterprise Application: Use Client Credentials flow
        credential = ClientSecretCredential(
            config.AAD_TENANT_ID,
            config.TEST_ACCOUNT_CLIENT_ID,
            config.TEST_ACCOUNT_CLIENT_SECRET,
            connection_verify=verify,
            authority=cloud.get_aad_authority_fqdn()
        )
        token = credential.get_token(f'{scope_uri}/.default')
    else:
        # Logging in as a User: Use Resource Owner Password Credentials flow
        credential = UsernamePasswordCredential(
            config.TEST_APP_ID,
            config.TEST_USER_NAME,
            config.TEST_USER_PASSWORD,
            connection_verify=verify,
            authority=cloud.get_aad_authority_fqdn(),
            tenant_id=config.AAD_TENANT_ID
        )
        token = credential.get_token(f'{scope_uri}/user_impersonation')

    return token.token


def assert_status(response: Response, expected_status: List[int] = [200], message_prefix: str = "Unexpected HTTP Status"):
    assert response.status_code in expected_status, \
        f"{message_prefix}. Expected: {expected_status}. Actual: {response.status_code}. Response text: {response.text}"


def _decode_jwt_payload(token: str) -> dict:
    """Decode a JWT token and return the payload as a dictionary."""
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {}

        # Decode the payload (second part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes.decode('utf-8'))
    except Exception as e:
        LOGGER.warning("Failed to decode JWT: %s", e)
        return {}


def _get_roles_from_token(token: str) -> List[str]:
    """Extract roles from a JWT token."""
    payload = _decode_jwt_payload(token)
    roles = payload.get('roles', [])
    if isinstance(roles, list):
        return roles
    return []


def _extract_scope_uri_from_workspace(workspace: dict) -> Optional[str]:
    """Extract the scope URI from a workspace dict for token requests."""
    scope_id = workspace.get("properties", {}).get("scope_id", "")
    if not scope_id:
        return None
    # Cope with the fact that scope_id can have api:// at the front
    return f"api://{scope_id.replace('api://', '')}"


async def ensure_automation_admin_has_airlock_role(workspace_id: str, admin_token: str, verify: bool) -> None:
    await _ensure_automation_admin_has_role(workspace_id, admin_token, verify, role_name="Airlock Manager")


async def ensure_automation_admin_has_workspace_owner_role(workspace_id: str, admin_token: str, verify: bool) -> None:
    await _ensure_automation_admin_has_role(workspace_id, admin_token, verify, role_name="WorkspaceOwner")


async def _ensure_automation_admin_has_role(workspace_id: str, admin_token: str, verify: bool, role_name: str) -> None:
    """Assign the automation admin identity to a workspace role via the TRE API."""
    if workspace_id == "":
        LOGGER.info("Workspace ID missing; skipping %s assignment", role_name)
        return

    if not _has_automation_identity():
        LOGGER.info("No automation admin identity configured; skipping %s assignment", role_name)
        return

    workspace = await _wait_for_user_management_configuration(workspace_id, admin_token, verify, role_name)
    if workspace is None:
        return

    role_id = await _get_workspace_role_id(workspace_id, admin_token, verify, role_name=role_name)
    if role_id is None:
        LOGGER.warning("%s role not found for workspace %s; skipping assignment", role_name, workspace_id)
        return

    user_object_id = await _get_automation_admin_object_id(verify)
    if user_object_id is None:
        LOGGER.warning("Unable to determine automation admin directory object id; skipping %s assignment", role_name)
        return

    scope_uri = _extract_scope_uri_from_workspace(workspace)
    await _assign_workspace_role_via_api(workspace_id, role_id, user_object_id, admin_token, verify, role_name, scope_uri)


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


# Map display names to role values used in tokens
ROLE_DISPLAY_TO_VALUE = {
    "Airlock Manager": "AirlockManager",
    "WorkspaceOwner": "WorkspaceOwner",
    "Workspace Owner": "WorkspaceOwner",
    "WorkspaceResearcher": "WorkspaceResearcher",
    "Workspace Researcher": "WorkspaceResearcher",
}


async def _assign_workspace_role_via_api(
    workspace_id: str,
    role_id: str,
    user_id: str,
    admin_token: str,
    verify: bool,
    role_name: str,
    scope_uri: Optional[str]
) -> None:
    """
    Assign a user/service principal to an app role via the TRE API.
    The API automatically uses direct app role assignment for service principals,
    which propagates to tokens immediately (no 5-15 min group membership delay).

    After assignment, verifies that the role appears in newly issued tokens
    by polling with retry to handle Entra ID propagation delays.
    """
    expected_role_value = ROLE_DISPLAY_TO_VALUE.get(role_name, role_name)

    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        headers = get_auth_header(admin_token)
        body = {
            "user_ids": [user_id],
            "role_id": role_id
        }
        response = await client.post(
            get_full_endpoint(f"/api/workspaces/{workspace_id}/users/assign"),
            headers=headers,
            json=body,
            timeout=TIMEOUT
        )

        if response.status_code == status.HTTP_202_ACCEPTED:
            LOGGER.info("App role assignment succeeded for %s role in workspace %s", role_name, workspace_id)
        else:
            LOGGER.warning(
                "App role assignment failed for %s role in workspace %s: %s - %s",
                role_name, workspace_id, response.status_code, response.text
            )
            return  # Don't attempt verification if assignment failed

    # Verify the role appears in newly issued tokens
    if scope_uri is None:
        LOGGER.warning("No workspace scope URI for %s; skipping role verification", workspace_id)
        await asyncio.sleep(5)  # Fall back to simple wait
        return

    await _verify_role_in_token(workspace_id, scope_uri, expected_role_value, role_name, verify)


async def _verify_role_in_token(
    workspace_id: str,
    scope_uri: str,
    expected_role_value: str,
    role_name: str,
    verify: bool
) -> None:
    """Poll for fresh tokens until the expected role appears."""
    loop = asyncio.get_running_loop()
    for attempt in range(ROLE_VERIFICATION_MAX_ATTEMPTS):
        # Get a fresh token for the workspace
        try:
            token = await loop.run_in_executor(None, functools.partial(get_token, scope_uri, verify))
            roles_in_token = _get_roles_from_token(token)

            if expected_role_value in roles_in_token:
                LOGGER.info(
                    "Verified %s role (%s) appears in token for workspace %s (attempt %s/%s)",
                    role_name, expected_role_value, workspace_id, attempt + 1, ROLE_VERIFICATION_MAX_ATTEMPTS
                )
                return

            LOGGER.info(
                "Role %s not yet in token for workspace %s, current roles: %s (attempt %s/%s)",
                expected_role_value, workspace_id, roles_in_token, attempt + 1, ROLE_VERIFICATION_MAX_ATTEMPTS
            )
        except Exception as e:
            LOGGER.warning(
                "Error getting token for role verification in workspace %s: %s (attempt %s/%s)",
                workspace_id, e, attempt + 1, ROLE_VERIFICATION_MAX_ATTEMPTS
            )

        await asyncio.sleep(ROLE_VERIFICATION_SLEEP_SECONDS)

    LOGGER.warning(
        "Role %s never appeared in token for workspace %s after %s attempts",
        expected_role_value, workspace_id, ROLE_VERIFICATION_MAX_ATTEMPTS
    )


async def _get_automation_admin_object_id(verify: bool) -> Optional[str]:
    """Get the directory object ID for the automation admin (user or service principal)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(_get_directory_object_id_via_graph, verify))


async def _wait_for_user_management_configuration(workspace_id: str, admin_token: str, verify: bool, role_name: str) -> Optional[dict]:
    """Poll the workspace until Entra ID role/group data is available. Returns workspace dict or None."""
    for attempt in range(ROLE_ASSIGNMENT_MAX_ATTEMPTS):
        workspace = await _get_workspace_details(workspace_id, admin_token, verify)
        if _workspace_supports_user_management(workspace):
            return workspace

        if _workspace_cannot_support_user_management(workspace):
            LOGGER.warning("Workspace %s does not support user management; skipping %s assignment", workspace_id, role_name)
            return None

        LOGGER.info("Waiting for workspace %s user management config (%s/%s)", workspace_id, attempt + 1, ROLE_ASSIGNMENT_MAX_ATTEMPTS)
        await asyncio.sleep(ROLE_ASSIGNMENT_SLEEP_SECONDS)

    LOGGER.warning("Workspace %s never exposed user management config; skipping %s assignment", workspace_id, role_name)
    return None


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
    with httpx.Client(headers=headers, timeout=TIMEOUT, verify=verify) as client:
        if _is_service_principal_auth():
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
