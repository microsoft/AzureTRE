import logging
from httpx import AsyncClient, Timeout
from typing import Tuple
from e2e_tests.helpers import get_auth_header, get_full_endpoint, get_msgraph_token, get_token

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)


async def get_workspace(client, workspace_id: str, headers) -> dict:
    full_endpoint = get_full_endpoint(f"/api/workspaces/{workspace_id}")

    response = await client.get(full_endpoint, headers=headers, timeout=TIMEOUT)
    if response.status_code == 200:
        return response.json()["workspace"]
    else:
        LOGGER.error(f"Non 200 response in get_workspace: {response.status_code}")
        LOGGER.error(f"Full response: {response}")
        raise Exception("Non 200 response in get_workspace")


async def get_identifier_uri(client, workspace_id: str, auth_headers) -> str:
    workspace = await get_workspace(client, workspace_id, auth_headers)

    if ("properties" not in workspace):
        raise Exception("Properties not found in workspace.")

    if ("scope_id" not in workspace["properties"]):
        raise Exception("Scope Id not found in workspace properties.")

    # Cope with the fact that scope id can have api:// at the front.
    return f"api://{workspace['properties']['scope_id'].replace('api://', '')}"


async def get_workspace_auth_details(admin_token, workspace_id, verify) -> Tuple[str, str]:
    async with AsyncClient(verify=verify) as client:
        auth_headers = get_auth_header(admin_token)
        scope_uri = await get_identifier_uri(client, workspace_id, auth_headers)
        access_token = get_token(scope_uri)

        return access_token, scope_uri


async def assign_airlock_manager_role(admin_token, workspace_id, verify) -> None:
    async with AsyncClient(verify=verify) as client:
        access_token = get_msgraph_token()
        auth_headers = get_auth_header(admin_token)
        workspace = await get_workspace(client, workspace_id, auth_headers)

        app_sp_id = workspace.get("properties", {}).get("sp_id")
        app_role_id = workspace.get("properties", {}).get("app_role_id_workspace_airlock_manager")
        user_object_id = workspace["user"]["id"]

        graph_api_url = "https://graph.microsoft.com/v1.0"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # check if the role is already assigned
        check_response = await client.get(
            f"{graph_api_url}/servicePrincipals/{user_object_id}/appRoleAssignments",
            headers=headers
        )
        if check_response.status_code != 200:
            LOGGER.error(f"Failed to check role assignment for user {user_object_id}: {check_response.status_code}")
            raise Exception(f"Failed to check role assignment for user {user_object_id}: {check_response.status_code}")

        assignments = check_response.json().get('value', [])

        if any(a['appRoleId'] == app_role_id for a in assignments):
            LOGGER.info(f"Role Airlock Manager already assigned to user {user_object_id} in workspace {workspace_id}")
            return

        payload = {
            "principalId": user_object_id,
            "resourceId": app_sp_id,
            "appRoleId": app_role_id
        }

        response = await client.post(
            f"{graph_api_url}/servicePrincipals/{user_object_id}/appRoleAssignments",
            headers=headers,
            json=payload
        )

        if response.status_code != 201:
            LOGGER.error(f"Failed to assign Airlock Manager to workspace {workspace_id}: {response.status_code}")
            raise Exception(f"Failed to assign role Airlock Manager to workspace {workspace_id}: {response.status_code}")
