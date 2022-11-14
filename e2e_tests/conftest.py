import pytest
import asyncio
from typing import Tuple
import config
import logging

from resources.resource import post_resource, disable_and_delete_resource
from resources.workspace import get_workspace_auth_details
from resources import strings
from helpers import get_admin_token


LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio


def pytest_addoption(parser):
    parser.addoption("--verify", action="store", default="true")


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture(scope="session")
def verify(pytestconfig):
    if pytestconfig.getoption("verify").lower() == "true":
        return True
    elif pytestconfig.getoption("verify").lower() == "false":
        return False


async def create_or_get_test_workspace(auth_type: str, verify: bool, pre_created_workspace_id: str = "", client_id: str = "", client_secret: str = "") -> Tuple[str, str]:
    if pre_created_workspace_id != "":
        return f"/workspaces/{pre_created_workspace_id}", pre_created_workspace_id

    LOGGER.info("Creating workspace")
    payload = {
        "templateName": strings.BASE_WORKSPACE,
        "properties": {
            "display_name": "E2E test workspace",
            "description": "Test workspace for E2E tests",
            "address_space_size": "small",
            "auth_type": auth_type
        }
    }
    if auth_type == "Manual":
        payload["properties"]["client_id"] = client_id
        payload["properties"]["client_secret"] = client_secret

    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    admin_token = await get_admin_token(verify=verify)
    workspace_path, workspace_id = await post_resource(payload, strings.API_WORKSPACES, access_token=admin_token, verify=verify)
    return workspace_path, workspace_id


async def clean_up_test_workspace(pre_created_workspace_id: str, workspace_path: str, verify: bool):
    # Only delete the workspace if it wasn't pre-created
    if pre_created_workspace_id == "":
        LOGGER.info("Deleting workspace")
        admin_token = await get_admin_token(verify=verify)
        await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)


@pytest.fixture(scope="session")
async def setup_test_workspace(verify) -> Tuple[str, str, str]:
    pre_created_workspace_id = config.TEST_WORKSPACE_ID
    # Set up
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Manual", verify=verify, pre_created_workspace_id=pre_created_workspace_id, client_id=config.TEST_WORKSPACE_APP_ID, client_secret=config.TEST_WORKSPACE_APP_SECRET)

    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    yield workspace_path, workspace_id, workspace_owner_token

    # Tear-down
    await clean_up_test_workspace(pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify)


@pytest.fixture(scope="session")
async def setup_test_aad_workspace(verify) -> Tuple[str, str, str]:
    pre_created_workspace_id = config.TEST_AAD_WORKSPACE_ID
    # Set up
    workspace_path, workspace_id = await create_or_get_test_workspace(auth_type="Automatic", verify=verify, pre_created_workspace_id=pre_created_workspace_id)

    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    yield workspace_path, workspace_id, workspace_owner_token

    # Tear-down
    await clean_up_test_workspace(pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify)


@pytest.fixture(scope="session")
async def setup_test_workspace_service(verify, setup_test_workspace) -> Tuple[str, str, str, str, str]:
    workspace_path, workspace_id, workspace_owner_token = setup_test_workspace
    pre_created_workspace_service_id = config.TEST_WORKSPACE_SERVICE_ID

    if pre_created_workspace_service_id == "":
        # create a guac service
        service_payload = {
            "templateName": strings.GUACAMOLE_SERVICE,
            "properties": {
                "display_name": "Workspace service test",
                "description": ""
            }
        }

        workspace_service_path, workspace_service_id = await post_resource(
            payload=service_payload,
            endpoint=f'/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}',
            access_token=workspace_owner_token,
            verify=verify)
    else:
        workspace_service_path = f"{workspace_path}/{strings.API_WORKSPACE_SERVICES}/{config.TEST_WORKSPACE_SERVICE_ID}"
        workspace_service_id = config.TEST_WORKSPACE_SERVICE_ID

    yield workspace_service_path, workspace_service_id, workspace_path, workspace_id, workspace_owner_token

    if pre_created_workspace_service_id == "":
        admin_token = await get_admin_token(verify=verify)
        await disable_and_delete_resource(f'/api{workspace_path}', admin_token, verify)
