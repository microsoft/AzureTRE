"""Upgrade resources that an earlier release created with Porter parameter overrides.

Resource Processor versions before 0.13.10 passed the parameters of each action as Porter command-line
overrides, and Porter keeps these overrides with the installation. The current Resource Processor stops a
custom action or an uninstall while the overrides exist. An upgrade with the current template version
clears them.

The seed case runs on a TRE at an earlier release. It creates a workspace with a Guacamole service and two
Windows VMs, disables the second VM and keeps all of them. The verify case runs after the core upgrade with
the current code and follows the procedure in `upgrading-resources.md`.
"""

import asyncio
import logging

from httpx import AsyncClient
import pytest
from starlette import status

from e2e_tests import config
from e2e_tests.conftest import (
    clean_up_test_workspace,
    create_or_get_test_workpace_service,
    create_or_get_test_workspace,
    get_workspace_owner_token,
)
from e2e_tests.helpers import assert_status, get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources import strings
from e2e_tests.resources.deployment import check_deployment
from e2e_tests.resources.resource import TIMEOUT, get_resource, post_resource
from e2e_tests.resources.sql_lifecycle import TERMINAL_STATES, sql_lifecycle
from e2e_tests.resources.sql_probe import COMPUTE_API, arm_client

LOGGER = logging.getLogger(__name__)
SEED_NAME = "E2E Porter upgrade seed"
ACTION_VM = "Porter upgrade action VM"
UNINSTALL_VM = "Porter upgrade uninstall VM"
# The Resource Processor reports this text when stored overrides stop an action.
UPGRADE_REQUIRED = "legacy Porter parameter overrides"


def require_test_app():
    if not config.TEST_WORKSPACE_APP_ID or not config.TEST_WORKSPACE_APP_SECRET:
        raise ValueError("Porter upgrade validation requires a configured manual test workspace application")


def vm_payload(name):
    return {
        "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
        "properties": {
            "display_name": name,
            "description": "Keeps the Porter parameter overrides of an earlier release",
            "os_image": "Windows 11",
            "vm_size": "2 CPU | 8GB RAM",
            # CI uses a service principal, so the bundle cannot derive a username from its owner.
            "admin_username": "researcher",
            "shared_storage_access": False,
            **{
                f"install_{tool}": False
                for tool in ("azure_cli", "vscode", "storage_explorer", "git", "python_tools", "r_tools")
            },
        },
    }


async def find_seed(admin_token, verify):
    """Return the seed workspace, or None. More than one seed workspace is an error."""
    workspaces = (await get_resource("/api/workspaces", admin_token, verify))["workspaces"]
    seeds = [w for w in workspaces if w["properties"].get("display_name") == SEED_NAME]
    if len(seeds) > 1:
        raise ValueError(f"Found {len(seeds)} Porter upgrade seed workspaces")
    return seeds[0] if seeds else None


async def seed_vms(workspace_path, token, verify):
    """Return the action VM and the uninstall VM of the seed workspace."""
    services = (await get_resource(f"/api{workspace_path}/{strings.API_WORKSPACE_SERVICES}", token, verify))[
        "workspaceServices"
    ]
    guacamole = [s for s in services if s["templateName"] == strings.GUACAMOLE_SERVICE]
    if len(guacamole) != 1:
        raise ValueError(f"Found {len(guacamole)} Guacamole services in the seed workspace")
    LOGGER.info("Seed Guacamole service at template version %s", guacamole[0]["templateVersion"])
    service_path = guacamole[0]["resourcePath"]
    vms = (await get_resource(f"/api{service_path}/{strings.API_USER_RESOURCES}", token, verify))["userResources"]
    found = {}
    for name in (ACTION_VM, UNINSTALL_VM):
        matches = [vm for vm in vms if vm["properties"].get("display_name") == name]
        if len(matches) != 1:
            raise ValueError(f"Found {len(matches)} seed VMs with the name {name}")
        found[name] = matches[0]
        LOGGER.info("%s at template version %s", name, matches[0]["templateVersion"])
    return found[ACTION_VM], found[UNINSTALL_VM]


async def finished(client, operation_endpoint, token):
    """Wait for an operation and return its status and its messages."""
    while True:
        state, message, steps = await check_deployment(client, operation_endpoint, token)
        if state in TERMINAL_STATES:
            return state, f"{message} {steps}"
        await asyncio.sleep(30)


async def send_action(resource_path, action, token, verify):
    """Send a custom action and return the status and the messages of its operation."""
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        response = await client.post(
            get_full_endpoint(f"/api{resource_path}/invoke-action"),
            headers=get_auth_header(token),
            params={"action": action},
        )
        assert_status(response, [status.HTTP_202_ACCEPTED], f"The {action} action could not be sent")
        return await finished(client, response.headers["Location"], token)


async def send_delete(resource_path, token, verify):
    """Delete a disabled resource and return the status and the messages of its operation."""
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        headers = get_auth_header(token)
        headers["etag"] = "*"
        response = await client.delete(get_full_endpoint(f"/api{resource_path}"), headers=headers)
        assert_status(response, [status.HTTP_200_OK], "The resource could not be deleted")
        return await finished(client, response.headers["Location"], token)


async def upgrade_in_place(resource_path, token, verify):
    """Upgrade a resource to its current template version with the documented PATCH."""
    record = (await get_resource(f"/api{resource_path}", token, verify))["userResource"]
    version = record["templateVersion"]
    await post_resource(
        {"templateVersion": version},
        f"/api{resource_path}",
        token,
        verify,
        method="PATCH",
        etag=record["_etag"],
    )
    record = (await get_resource(f"/api{resource_path}", token, verify))["userResource"]
    assert record["templateVersion"] == version
    assert record["deploymentStatus"] == strings.RESOURCE_STATUS_UPDATED


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.porter_upgrade_seed
@pytest.mark.timeout(150 * 60)
async def test_seed_resources_with_legacy_overrides(verify):
    require_test_app()
    admin_token = await get_admin_token(verify)
    if await find_seed(admin_token, verify) is not None:
        raise ValueError("A Porter upgrade seed workspace already exists")
    workspace_path, workspace_id = await create_or_get_test_workspace(
        auth_type="Manual",
        verify=verify,
        client_id=config.TEST_WORKSPACE_APP_ID,
        client_secret=config.TEST_WORKSPACE_APP_SECRET,
        properties={"display_name": SEED_NAME},
    )
    try:
        token = await get_workspace_owner_token(workspace_id, verify)
        service_path, _ = await create_or_get_test_workpace_service(workspace_path, token, "", verify)
        endpoint = f"/api{service_path}/{strings.API_USER_RESOURCES}"
        await post_resource(vm_payload(ACTION_VM), endpoint, token, verify)
        uninstall_path, _ = await post_resource(vm_payload(UNINSTALL_VM), endpoint, token, verify)
        # The earlier Resource Processor runs the disable as an upgrade with overrides, so the overrides stay.
        await post_resource({"isEnabled": False}, f"/api{uninstall_path}", token, verify, method="PATCH")
        LOGGER.info("Seed workspace %s has a Guacamole service and two Windows VMs", workspace_id)
    except BaseException:
        # The verify case needs a complete seed. Do not keep a partial one.
        await clean_up_test_workspace("", workspace_path, verify)
        raise


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.porter_upgrade_verify
@pytest.mark.timeout(285 * 60)
async def test_upgrade_clears_legacy_overrides(verify):
    require_test_app()
    admin_token = await get_admin_token(verify)
    seed = await find_seed(admin_token, verify)
    if seed is None:
        raise ValueError("Run the porter_upgrade_seed case on the earlier release first")
    workspace_id = seed["id"]
    workspace_path = f"/workspaces/{workspace_id}"
    async with sql_lifecycle(verify, deadline_variable="PORTER_UPGRADE_VALIDATION_DEADLINE") as resources:
        resources.own(workspace_path, clean_up_test_workspace, "", workspace_path, verify)
        LOGGER.info("Seed workspace %s at template version %s", workspace_id, seed["templateVersion"])
        token = await get_workspace_owner_token(workspace_id, verify)
        action_vm, uninstall_vm = await seed_vms(workspace_path, token, verify)
        assert action_vm["isEnabled"] and not uninstall_vm["isEnabled"]
        action_path = action_vm["resourcePath"]
        uninstall_path = uninstall_vm["resourcePath"]
        uninstall_id = uninstall_vm["properties"]["azure_resource_id"]

        async with arm_client() as arm:
            # The stored overrides stop a custom action and an uninstall before Porter runs.
            state, message = await send_action(action_path, "stop", token, verify)
            assert state == strings.RESOURCE_ACTION_STATUS_FAILED, f"The stop action ended with {state}"
            assert UPGRADE_REQUIRED in message, "The stop action failed without the upgrade-required message"
            state, message = await send_delete(uninstall_path, token, verify)
            assert state == strings.RESOURCE_STATUS_DELETING_FAILED, f"The uninstall ended with {state}"
            assert UPGRADE_REQUIRED in message, "The uninstall failed without the upgrade-required message"
            assert await arm.request("GET", uninstall_id, COMPUTE_API, missing_ok=True) is not None
            LOGGER.info("The stored overrides stopped the custom action and the uninstall")

            # An upgrade with the current template version clears the overrides.
            for path in (action_path, uninstall_path):
                await upgrade_in_place(path, token, verify)
            LOGGER.info("The upgrades with the current template versions passed")

            for action in ("stop", "start"):
                state, _ = await send_action(action_path, action, token, verify)
                assert state == strings.RESOURCE_ACTION_STATUS_SUCCEEDED, f"The {action} action ended with {state}"
            state, _ = await send_delete(uninstall_path, token, verify)
            assert state == strings.RESOURCE_STATUS_DELETED, f"The uninstall after the upgrade ended with {state}"
            assert await arm.request("GET", uninstall_id, COMPUTE_API, missing_ok=True) is None
            LOGGER.info("The custom actions and the uninstall passed after the upgrade")

        # The workspace disable upgrades each child resource, so the cascade delete must pass.
        await resources.delete_now(workspace_path)
        LOGGER.info("The seed workspace and its resources were deleted")
