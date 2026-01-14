import asyncio
import functools
import logging
import random
import re
import subprocess
from pathlib import Path
from typing import Tuple

import config
import pytest

from resources.resource import post_resource, disable_and_delete_resource
from resources.workspace import get_workspace_auth_details
from resources import strings as resource_strings
from helpers import get_admin_token, ensure_automation_admin_has_airlock_role, ensure_automation_admin_has_workspace_owner_role


LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio(loop_scope="session")

_MANUALLY_CREATED_APP_NAME_PREFIX = "TRE E2E Manual Workspace"
_CREATE_MANUAL_APP_SCRIPT = Path(__file__).resolve().parents[1] / "devops" / "scripts" / "aad" / "create_workspace_application.sh"
_MANUAL_APP_CLIENT_ID_PATTERN = re.compile(r"Workspace Application Client ID:\s*([0-9a-f-]+)")


def pytest_addoption(parser):
    parser.addoption("--verify", action="store", default="true")


@pytest.fixture(scope="session")
def verify(pytestconfig):
    option_value = pytestconfig.getoption("verify").lower()
    if option_value == "true":
        return True
    if option_value == "false":
        return False
    raise ValueError("--verify must be 'true' or 'false'")


def _run_manual_app_script(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout + completed.stderr


async def _provision_manually_created_application_client_id() -> str:
    if not _CREATE_MANUAL_APP_SCRIPT.exists():
        raise FileNotFoundError(f"Unable to locate create_workspace_application.sh at {_CREATE_MANUAL_APP_SCRIPT}")

    application_admin_client_id = config.API_CLIENT_ID
    if application_admin_client_id == "":
        raise ValueError("API_CLIENT_ID must be set to provision a manually created workspace application")

    command = [
        str(_CREATE_MANUAL_APP_SCRIPT),
        "--name",
        _MANUALLY_CREATED_APP_NAME_PREFIX,
        "--application-admin-clientid",
        application_admin_client_id
    ]

    loop = asyncio.get_running_loop()
    output = await loop.run_in_executor(None, functools.partial(_run_manual_app_script, command))

    match = _MANUAL_APP_CLIENT_ID_PATTERN.search(output)
    if not match:
        raise RuntimeError(f"Unable to parse workspace application client ID from script output: {output}")

    client_id = match.group(1)
    LOGGER.info("Ensured manually created workspace application exists: %s", client_id)
    return client_id


async def create_or_get_test_workspace(
        auth_type: str,
        verify: bool,
        template_name: str = resource_strings.BASE_WORKSPACE,
        pre_created_workspace_id: str = "",
        client_id: str = "") -> Tuple[str, str]:
    if pre_created_workspace_id != "":
        return f"/workspaces/{pre_created_workspace_id}", pre_created_workspace_id

    LOGGER.info(f"Creating workspace {template_name}")

    description = " ".join([x.capitalize() for x in template_name.split("-")[2:]])
    payload = {
        "templateName": template_name,
        "properties": {
            "display_name": f"E2E {description} workspace ({auth_type} AAD)",
            "description": f"{template_name} test workspace for E2E tests",
            "auth_type": auth_type,
            "address_space_size": "small",
            "create_aad_groups": True
        }
    }
    if config.TEST_WORKSPACE_APP_PLAN != "":
        payload["properties"]["app_service_plan_sku"] = config.TEST_WORKSPACE_APP_PLAN

    if auth_type == "Manual":
        payload["properties"]["client_id"] = client_id

    admin_token = await get_admin_token(verify=verify)
    # TODO: Temp fix to solve creation of workspaces - https://github.com/microsoft/AzureTRE/issues/2986
    await asyncio.sleep(random.uniform(1, 9))
    workspace_path, workspace_id = await post_resource(payload, resource_strings.API_WORKSPACES, access_token=admin_token, verify=verify)

    LOGGER.info(f"Workspace {workspace_id} {template_name} created")

    # Wait for workspace to be fully deployed before attempting role assignments
    from resources.resource import wait_for
    await wait_for(workspace_path, admin_token, verify)

    await ensure_automation_admin_has_airlock_role(workspace_id, admin_token, verify)

    if auth_type == "Manual" and client_id != "":
        await ensure_automation_admin_has_workspace_owner_role(workspace_id, admin_token, verify)

    return workspace_path, workspace_id


async def create_or_get_test_workpace_service(workspace_path, workspace_owner_token, pre_created_workspace_service_id, verify):
    if pre_created_workspace_service_id != "":
        workspace_service_id = pre_created_workspace_service_id
        workspace_service_path = f"{workspace_path}/{resource_strings.API_WORKSPACE_SERVICES}/{workspace_service_id}"
        return workspace_service_path, workspace_service_id

    # create a guac service
    service_payload = {
        "templateName": resource_strings.GUACAMOLE_SERVICE,
        "properties": {
            "display_name": "Workspace service test",
            "description": ""
        }
    }

    workspace_service_path, workspace_service_id = await post_resource(
        payload=service_payload,
        endpoint=f'/api{workspace_path}/{resource_strings.API_WORKSPACE_SERVICES}',
        access_token=workspace_owner_token,
        verify=verify)

    return workspace_service_path, workspace_service_id


async def clean_up_test_workspace(pre_created_workspace_id: str, workspace_path: str, verify: bool):
    # Only delete the workspace if it wasn't pre-created
    if pre_created_workspace_id == "":
        LOGGER.info(f"Deleting workspace {pre_created_workspace_id}")
        await disable_and_delete_tre_resource(workspace_path, verify)


async def clean_up_test_workspace_service(pre_created_workspace_service_id: str, workspace_service_path: str, workspace_id: str, verify: bool):
    if pre_created_workspace_service_id == "":
        LOGGER.info(f"Deleting workspace service {pre_created_workspace_service_id}")
        await disable_and_delete_ws_resource(workspace_service_path, workspace_id, verify)


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_workspace(verify) -> Tuple[str, str, str]:
    pre_created_workspace_id = config.TEST_WORKSPACE_ID
    # Set up - uses a pre created app reg as has appropriate roles assigned
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Automatic", verify=verify, pre_created_workspace_id=pre_created_workspace_id)

    yield workspace_path, workspace_id

    # Tear-down
    await clean_up_test_workspace(pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify)


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_workspace_and_guacamole_service(setup_test_workspace, verify):
    # Set up
    workspace_path, workspace_id = setup_test_workspace
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    pre_created_workspace_service_id = config.TEST_WORKSPACE_SERVICE_ID
    workspace_service_path, workspace_service_id = await create_or_get_test_workpace_service(
        workspace_path,
        workspace_owner_token=workspace_owner_token,
        pre_created_workspace_service_id=pre_created_workspace_service_id,
        verify=verify)

    yield workspace_path, workspace_id, workspace_service_path, workspace_service_id

    await clean_up_test_workspace_service(pre_created_workspace_service_id, workspace_service_path, workspace_id, verify)


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_aad_workspace(verify) -> Tuple[str, str, str]:
    pre_created_workspace_id = config.TEST_AAD_WORKSPACE_ID
    # Set up
    workspace_path, workspace_id = await create_or_get_test_workspace(auth_type="Automatic", verify=verify, pre_created_workspace_id=pre_created_workspace_id)

    yield workspace_path, workspace_id

    # Tear-down
    await clean_up_test_workspace(pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify)


@pytest.fixture(scope="session")
async def setup_manually_created_application_workspace(verify) -> Tuple[str, str]:
    client_id = await _provision_manually_created_application_client_id()

    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Manual",
        verify=verify,
        client_id=client_id)

    yield workspace_path, workspace_id

    await clean_up_test_workspace(pre_created_workspace_id="", workspace_path=workspace_path, verify=verify)


async def get_workspace_owner_token(workspace_id, verify):
    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    return workspace_owner_token


async def disable_and_delete_ws_resource(resource_path, workspace_id, verify):
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
    await disable_and_delete_resource(f'/api{resource_path}', workspace_owner_token, verify)


async def disable_and_delete_tre_resource(resource_path, verify):
    admin_token = await get_admin_token(verify)
    await disable_and_delete_resource(f'/api{resource_path}', admin_token, verify)


# Session scope isn't in effect with python-xdist: https://github.com/microsoft/AzureTRE/issues/2868
@pytest.fixture(scope="session")
async def setup_test_airlock_import_review_workspace_and_guacamole_service(verify) -> Tuple[str, str, str, str, str]:
    pre_created_workspace_id = config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_ID
    # Set up
    workspace_path, workspace_id = await create_or_get_test_workspace(auth_type="Automatic", verify=verify, template_name=resource_strings.AIRLOCK_IMPORT_REVIEW_WORKSPACE, pre_created_workspace_id=pre_created_workspace_id)

    admin_token = await get_admin_token(verify=verify)
    workspace_owner_token, _ = await get_workspace_auth_details(admin_token=admin_token, workspace_id=workspace_id, verify=verify)
    pre_created_workspace_service_id = config.TEST_AIRLOCK_IMPORT_REVIEW_WORKSPACE_SERVICE_ID

    workspace_service_path, workspace_service_id = await create_or_get_test_workpace_service(
        workspace_path,
        workspace_owner_token=workspace_owner_token,
        pre_created_workspace_service_id=pre_created_workspace_service_id,
        verify=verify)

    yield workspace_path, workspace_id, workspace_service_path, workspace_service_id

    # Tear-down in a cascaded way
    await clean_up_test_workspace(pre_created_workspace_id=pre_created_workspace_id, workspace_path=workspace_path, verify=verify)
