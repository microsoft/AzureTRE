"""Check that a Guacamole Linux VM finishes its Nexus-backed bootstrap."""

import pytest
from httpx import AsyncClient
from starlette import status

from e2e_tests.conftest import disable_and_delete_ws_resource, get_workspace_owner_token
from e2e_tests.helpers import assert_status, get_auth_header, get_full_endpoint
from e2e_tests.resources import strings
from e2e_tests.resources.deployment import install_done
from e2e_tests.resources.resource import TIMEOUT, wait_for


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

    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        response = await client.post(
            get_full_endpoint(f"/api{workspace_service_path}/{strings.API_USER_RESOURCES}"),
            headers=get_auth_header(workspace_owner_token),
            json=payload,
        )
        assert_status(response, [status.HTTP_202_ACCEPTED], "The Linux VM could not be created")
        # Capture the path before waiting, so a failed bootstrap can still be removed.
        resource_path = response.json()["operation"]["resourcePath"]
        try:
            await wait_for(
                install_done,
                client,
                response.headers["Location"],
                workspace_owner_token,
                [strings.RESOURCE_STATUS_DEPLOYMENT_FAILED],
            )
        finally:
            # Reused workspace/service fixtures do not delete their user resources.
            await disable_and_delete_ws_resource(resource_path, workspace_id, verify)
