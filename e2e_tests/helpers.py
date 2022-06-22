import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from httpx import AsyncClient, Timeout
import logging
from starlette import status

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
async def get_template(template_name, endpoint, token, verify):
    async with AsyncClient(verify=verify) as client:
        auth_headers = get_auth_header(token)
        full_endpoint = get_full_endpoint(endpoint)

        response = await client.get(f"{full_endpoint}/{template_name}", headers=auth_headers, timeout=TIMEOUT)
        yield response


async def get_shared_service_id_by_name(template_name: str, verify, token) -> Optional[dict]:
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        full_endpoint = get_full_endpoint('/api/shared-services')
        auth_headers = get_auth_header(token)

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        LOGGER.info(f'RESPONSE: {response}')
        assert (response.status_code == status.HTTP_200_OK), "Request to get shared services failed"

        shared_service_list = response.json()["sharedServices"]
        matching_shared_services = [
            service for service in shared_service_list
            if service["templateName"] == template_name and service["deploymentStatus"] == "deployed"]
        if len(matching_shared_services) == 0:
            return None
        assert len(matching_shared_services) == 1, f"There can be at most one deployed shared service with template name {template_name}"
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
