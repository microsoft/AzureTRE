from json import JSONDecodeError

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


async def get_shared_service_by_name(template_name: str, verify, token) -> Optional[dict]:
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        full_endpoint = get_full_endpoint('/api/shared-services')
        auth_headers = get_auth_header(token)

        response = await client.get(full_endpoint, headers=auth_headers, timeout=TIMEOUT)
        LOGGER.info(f'RESPONSE: {response}')
        assert (response.status_code == status.HTTP_200_OK), "Request to get shared services failed"

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

        assert (response.status_code == status.HTTP_302_FOUND)
        assert response.has_redirect_location

        location = response.headers["Location"]
        LOGGER.info("Returned redirect URL: %s", location)

        valid_redirection_contains = ["login", "microsoftonline", "oauth2", "authorize"]
        assert all(word in location for word in valid_redirection_contains), "Redirect URL doesn't apper to be valid"


async def get_admin_token(verify) -> str:
    async with AsyncClient(verify=verify) as client:
        responseJson = ""
        headers = {'Content-Type': "application/x-www-form-urlencoded"}
        if config.TEST_ACCOUNT_CLIENT_ID != "" and config.TEST_ACCOUNT_CLIENT_SECRET != "":
            # Use Client Credentials flow
            payload = f"grant_type=client_credentials&client_id={config.TEST_ACCOUNT_CLIENT_ID}&client_secret={config.TEST_ACCOUNT_CLIENT_SECRET}&scope=api://{config.API_CLIENT_ID}/.default"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/v2.0/token"

        else:
            # Use Resource Owner Password Credentials flow
            payload = f"grant_type=password&resource={config.API_CLIENT_ID}&username={config.TEST_USER_NAME}&password={config.TEST_USER_PASSWORD}&scope=api://{config.API_CLIENT_ID}/user_impersonation&client_id={config.TEST_APP_ID}"
            url = f"https://login.microsoftonline.com/{config.AAD_TENANT_ID}/oauth2/token"

        response = await client.post(url, headers=headers, content=payload)
        try:
            responseJson = response.json()
        except JSONDecodeError:
            assert False, "Failed to parse response as JSON: {} {}".format(response.status_code, response.content)

        assert "access_token" in responseJson, "Failed to get access_token: {}".format(response.content)
        token = responseJson["access_token"]
        assert token is not None, "Token not returned"
        return token if (response.status_code == status.HTTP_200_OK) else None
