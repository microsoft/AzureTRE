import logging
import config
from httpx import AsyncClient, Timeout
from azure.identity import ClientSecretCredential, UsernamePasswordCredential
from typing import Tuple
from e2e_tests import cloud
from e2e_tests.helpers import get_auth_header, get_full_endpoint

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
    return f"api://{workspace['properties']['scope_id'].replace('api://','')}"


async def get_workspace_auth_details(admin_token, workspace_id, verify) -> Tuple[str, str]:
    async with AsyncClient(verify=verify) as client:
        auth_headers = get_auth_header(admin_token)
        scope_uri = await get_identifier_uri(client, workspace_id, auth_headers)
    if config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != "":
        # Logging in as an Enterprise Application: Use Client Credentials flow
        credential = ClientSecretCredential(config.AAD_TENANT_ID, config.TEST_ACCOUNT_CLIENT_ID, config.TEST_ACCOUNT_CLIENT_SECRET, connection_verify=verify, authority=cloud.get_authority_domain())
        token = credential.get_token(f'{scope_uri}/.default')
    else:
        # Logging in as a User: Use Resource Owner Password Credentials flow
        credential = UsernamePasswordCredential(config.TEST_APP_ID, config.TEST_USER_NAME, config.TEST_USER_PASSWORD, connection_verify=verify, authority=cloud.get_authority_domain(), tenant_id=config.AAD_TENANT_ID)
        token = credential.get_token(f'{scope_uri}/user_impersonation')

    return token.token, scope_uri
