"""Check that a Guacamole Linux VM finishes its Nexus-backed bootstrap and runs its actions."""

import pytest

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.resources import strings
from e2e_tests.resources.resource import get_resource, temporary_resource
from e2e_tests.resources.nexus import nexus_prerequisites
from e2e_tests.resources.sql_probe import arm_client
from e2e_tests.resources.vm_actions import invoke_action, power_state, secret_version


pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.linux_vm
@pytest.mark.timeout(150 * 60)
async def test_create_guacamole_linux_vm(setup_test_workspace_and_guacamole_service, verify):
    _, workspace_id, workspace_service_path, _ = setup_test_workspace_and_guacamole_service
    payload = {
        "templateName": strings.GUACAMOLE_LINUX_USER_RESOURCE,
        "properties": {
            "display_name": "Nexus Linux bootstrap test",
            "description": "Verify jammy package installation and cloud-init completion",
            "os_image": "Ubuntu 22.04 LTS",
            "vm_size": "2 CPU | 8GB RAM",
            # CI uses a service principal, so the bundle cannot derive a username from its owner.
            "admin_username": "researcher",
        },
    }

    async with nexus_prerequisites(verify):
        workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
        async with temporary_resource(
            payload, f"/api{workspace_service_path}/{strings.API_USER_RESOURCES}", workspace_owner_token, verify
        ) as vm_path:
            await check_vm_actions(vm_path, workspace_id, verify)


async def check_vm_actions(vm_path, workspace_id, verify):
    """Run the VM actions and read their effect from Azure."""
    token = await get_workspace_owner_token(workspace_id, verify)
    vm_id = (await get_resource(f"/api{vm_path}", token, verify))["userResource"]["properties"]["azure_resource_id"]
    group = vm_id.split("/providers/", 1)[0]
    vault = f"kv-{f'{config.TRE_ID}-ws-{workspace_id[-4:]}'[-20:]}".lower()
    vault_id = f"{group}/providers/Microsoft.KeyVault/vaults/{vault}"
    secret_name = f"{vm_id.rsplit('/', 1)[1]}-admin-credentials"
    async with arm_client() as arm:
        assert await power_state(arm, vm_id) == "PowerState/running"
        await invoke_action(vm_path, "stop", await get_workspace_owner_token(workspace_id, verify), verify)
        assert await power_state(arm, vm_id) == "PowerState/deallocated"
        await invoke_action(vm_path, "start", await get_workspace_owner_token(workspace_id, verify), verify)
        assert await power_state(arm, vm_id) == "PowerState/running"
        version = await secret_version(arm, vault_id, secret_name)
        await invoke_action(vm_path, "reset_password", await get_workspace_owner_token(workspace_id, verify), verify)
        assert await secret_version(arm, vault_id, secret_name) != version, "reset_password kept the secret"
