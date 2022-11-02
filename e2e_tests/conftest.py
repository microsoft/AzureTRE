import pytest
from json import JSONDecodeError
from typing import Tuple
import config
from httpx import AsyncClient
import logging
from fastapi import status

from resources.resource import post_resource, disable_and_delete_resource
from resources.workspace import get_workspace_auth_details
from resources import strings as resource_strings


LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio


def pytest_addoption(parser):
    parser.addoption("--verify", action="store", default="true")


@pytest.fixture
def verify(pytestconfig):
    if pytestconfig.getoption("verify").lower() == "true":
        return True
    elif pytestconfig.getoption("verify").lower() == "false":
        return False


@pytest.fixture
async def admin_token(verify) -> str:
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
            assert False, "Failed to parse response as JSON: {}".format(response.content)

        assert "access_token" in responseJson, "Failed to get access_token: {}".format(response.content)
        token = responseJson["access_token"]
        assert token is not None, "Token not returned"
        return token if (response.status_code == status.HTTP_200_OK) else None


async def create_test_workspace(client_id: str, client_secret: str) -> Tuple[str, str]:
    LOGGER.info("Creating workspace")
    payload = {
        "templateName": resource_strings.BASE_WORKSPACE,
        "properties": {
            "display_name": "E2E test airlock flow",
            "description": "workspace for E2E airlock flow",
            "address_space_size": "small",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    }

    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    workspace_path, workspace_id = await post_resource(payload, resource_strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    return workspace_path, workspace_id


@pytest.fixture
async def setup_test_workspace(verify, admin_token) -> Tuple[str, str, str]:
    # Set up
    if config.TEST_AIRLOCK_WORKSPACE_ID == "":
        workspace_path, workspace_id = create_test_workspace(
            client_id=config.TEST_WORKSPACE_APP_ID, client_secret=config.TEST_ACCOUNT_CLIENT_SECRET)
    else:
        workspace_id = config.TEST_AIRLOCK_WORKSPACE_ID
        workspace_path = f"/workspaces/{workspace_id}"

    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    yield workspace_path, workspace_id, workspace_owner_token

    # Tear-down
    if config.TEST_AIRLOCK_WORKSPACE_ID == "":
        LOGGER.info("Deleting workspace")
        await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)


@pytest.fixture
async def setup_test_aad_workspace(verify, admin_token) -> Tuple[str, str, str]:
    workspace_path, workspace_id = create_test_workspace(client_id="auto_create", client_secret="")
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    yield workspace_path, workspace_id, workspace_owner_token

    # Tear-down
    LOGGER.info("Deleting workspace")
    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)
