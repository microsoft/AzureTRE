import pytest
from typing import Tuple
import config
import logging

from resources.resource import post_resource, disable_and_delete_resource
from resources.workspace import get_workspace_auth_details
from resources import strings as resource_strings
from helpers import get_admin_token


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


async def create_test_workspace(client_id: str, client_secret: str, verify: bool) -> Tuple[str, str]:
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
    LOGGER.info(f"Payload {payload}")

    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    admin_token = await get_admin_token(verify=verify)
    workspace_path, workspace_id = await post_resource(payload, resource_strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    return workspace_path, workspace_id


@pytest.fixture
async def setup_test_workspace(verify) -> Tuple[str, str, str]:
    # Set up
    if config.TEST_WORKSPACE_ID == "":
        workspace_path, workspace_id = await create_test_workspace(
            client_id=config.TEST_WORKSPACE_APP_ID, client_secret=config.TEST_WORKSPACE_APP_SECRET, verify=verify)
    else:
        workspace_id = config.TEST_WORKSPACE_ID
        workspace_path = f"/workspaces/{workspace_id}"

    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    yield workspace_path, workspace_id, workspace_owner_token

    # Tear-down
    if config.TEST_WORKSPACE_ID == "":
        LOGGER.info("Deleting workspace")
        admin_token = await get_admin_token(verify=verify)
        await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)


@pytest.fixture
async def setup_test_aad_workspace(verify) -> Tuple[str, str, str]:
    workspace_path, workspace_id = await create_test_workspace(client_id="auto_create", client_secret="", verify=verify)
    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)

    yield workspace_path, workspace_id, workspace_owner_token

    # Tear-down
    LOGGER.info("Deleting workspace")
    await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)
