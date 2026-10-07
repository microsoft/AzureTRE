"""Check that a Guacamole Linux VM finishes its Nexus-backed bootstrap."""

import pytest

from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.resources import strings
from e2e_tests.resources.resource import post_resource


pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.extended
@pytest.mark.linux_vm
@pytest.mark.timeout(75 * 60)
async def test_create_guacamole_linux_vm(setup_test_workspace_and_guacamole_service, verify):
    _, workspace_id, workspace_service_path, _ = setup_test_workspace_and_guacamole_service
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)
    payload = {
        "templateName": strings.GUACAMOLE_LINUX_USER_RESOURCE,
        "properties": {
            "display_name": "Nexus Linux bootstrap test",
            "description": "Verify jammy package installation and cloud-init completion",
            "os_image": "Ubuntu 22.04 LTS",
        },
    }

    # The operation waits for the cloud-init extension, and fails on bootstrap errors.
    # The session fixture removes the VM with its Guacamole service during teardown.
    await post_resource(
        payload,
        f"/api{workspace_service_path}/{strings.API_USER_RESOURCES}",
        workspace_owner_token,
        verify,
    )
