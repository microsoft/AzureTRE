import logging
import config
from httpx import AsyncClient, Timeout
from json import JSONDecodeError
from starlette import status
from typing import Tuple
from e2e_tests import cloud
from e2e_tests.helpers import get_auth_header, get_full_endpoint

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)
AAD_AUTHORITY_URL = cloud.get_aad_authority_url()


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
    return f"api://{workspace['properties']['scope_id'].replace('api://','')}"


async def get_workspace_auth_details(admin_token, workspace_id, verify) -> Tuple[str, str]:
    async with AsyncClient(verify=verify) as client:
        auth_headers = get_auth_header(admin_token)
        scope_uri = await get_identifier_uri(client, workspace_id, auth_headers)

        if config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != "":
            # Logging in as an Enterprise Application: Use Client Credentials flow
            payload = f"grant_type=client_credentials&client_id={config.TEST_ACCOUNT_CLIENT_ID}&client_secret={config.TEST_ACCOUNT_CLIENT_SECRET}&scope={scope_uri}/.default"
            url = f"{AAD_AUTHORITY_URL}/{config.AAD_TENANT_ID}/oauth2/v2.0/token"

        else:
            # Logging in as a User: Use Resource Owner Password Credentials flow
            payload = f"grant_type=password&resource={workspace_id}&username={config.TEST_USER_NAME}&password={config.TEST_USER_PASSWORD}&scope={scope_uri}/user_impersonation&client_id={config.TEST_APP_ID}"
            url = f"{AAD_AUTHORITY_URL}/{config.AAD_TENANT_ID}/oauth2/token"

        response = await client.post(url, headers=auth_headers, content=payload)
        try:
            responseJson = response.json()
        except JSONDecodeError:
            raise Exception("Failed to parse response as JSON: {}".format(response.content))

        if "access_token" not in responseJson or response.status_code != status.HTTP_200_OK:
            raise Exception("Failed to get access_token: {}".format(response.content))

        return responseJson["access_token"], scope_uri
