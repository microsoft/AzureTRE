import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager
from httpx import AsyncClient, Timeout, Response
import logging
from starlette import status
from azure.identity import ClientSecretCredential, UsernamePasswordCredential

import config
from e2e_tests import cloud

LOGGER = logging.getLogger(__name__)
TIMEOUT = Timeout(10, read=30)

azlogger = logging.getLogger("azure")
azlogger.setLevel(logging.WARN)


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
