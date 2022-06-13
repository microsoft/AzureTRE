import asyncio
from typing import Optional, Tuple
from contextlib import asynccontextmanager
from httpx import AsyncClient, Timeout
import logging
from starlette import status

from json import JSONDecodeError
import config


LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)


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
    if (config.TRE_URL != ""):
        return f"{config.TRE_URL}{endpoint}"
    else:
        return f"https://{config.TRE_ID}.{config.RESOURCE_LOCATION}.cloudapp.azure.com{endpoint}"


@asynccontextmanager
async def get_template(template_name, endpoint, admin_token, verify):
    async with AsyncClient(verify=verify) as client:
        headers = {'Authorization': f'Bearer {admin_token}'}
        full_endpoint = get_full_endpoint(endpoint)

        response = await client.get(f"{full_endpoint}/{template_name}", headers=headers, timeout=TIMEOUT)
        yield response


async def get_shared_service_id_by_name(template_name: str, verify, token) -> Optional[dict]:
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        full_endpoint = get_full_endpoint('/api/shared-services')
        auth_headers = get_auth_header(token)

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        LOGGER.info(f'RESPONSE: {response} {response.json()}')
        assert (response.status_code == status.HTTP_200_OK), "Request to get shared services failed"

        shared_service_list = response.json()["sharedServices"]
        matching_shared_services = [service for service in shared_service_list if service["templateName"] == template_name and service["isActive"]]
        if len(matching_shared_services) == 0:
            return None
        assert len(matching_shared_services) == 1, f"There can be at most one active shared service with template name {template_name}"
        return matching_shared_services[0]


async def ping_guacamole_workspace_service(workspace_id, workspace_service_id, token, verify) -> None:
    short_workspace_id = workspace_id[-4:]
    short_workspace_service_id = workspace_service_id[-4:]
    endpoint = f"https://guacamole-{config.TRE_ID}-ws-{short_workspace_id}-svc-{short_workspace_service_id}.azurewebsites.net/guacamole"
    headers = {'x-access-token': f'{token}'}
    terminal_http_status = [status.HTTP_200_OK,
                            status.HTTP_401_UNAUTHORIZED,
                            status.HTTP_403_FORBIDDEN,
                            status.HTTP_302_FOUND  # usually means auth header wasn't accepted
                            ]

    async with AsyncClient(verify=verify) as client:
        while (True):
            try:
                response = await client.get(url=endpoint, headers=headers, timeout=TIMEOUT)
                LOGGER.info(f"GUAC RESPONSE: {response}")

                if response.status_code in terminal_http_status:
                    break

                await asyncio.sleep(30)

            except Exception:
                LOGGER.exception("Generic execption in ping.")

        assert (response.status_code == status.HTTP_200_OK), "Guacamole cannot be reached"


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
    return f"api://{workspace['properties']['scope_id'].lstrip('api://')}"


async def get_workspace_auth_details(admin_token, workspace_id, verify) -> Tuple[str, str]:
    async with AsyncClient(verify=verify) as client:
        auth_headers = get_auth_header(admin_token)
        scope_uri = await get_identifier_uri(client, workspace_id, auth_headers)

        if config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != "":
            # Logging in as an Enterprise Application: Use Client Credentials flow
            payload = f"grant_type=client_credentials&client_id={config.TEST_ACCOUNT_CLIENT_ID}&client_secret={config.TEST_ACCOUNT_CLIENT_SECRET}&scope={scope_uri}/.default"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/v2.0/token"

        else:
            # Logging in as a User: Use Resource Owner Password Credentials flow
            payload = f"grant_type=password&resource={workspace_id}&username={config.TEST_USER_NAME}&password={config.TEST_USER_PASSWORD}&scope={scope_uri}/user_impersonation&client_id={config.TEST_APP_ID}"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/token"

        response = await client.post(url, headers=auth_headers, content=payload)
        try:
            responseJson = response.json()
        except JSONDecodeError:
            raise Exception("Failed to parse response as JSON: {}".format(response.content))

        if "access_token" not in responseJson or response.status_code != status.HTTP_200_OK:
            raise Exception("Failed to get access_token: {}".format(response.content))

        return responseJson["access_token"], scope_uri
