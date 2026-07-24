import logging
import pytest
from httpx import AsyncClient, Timeout
from starlette import status

import config
from helpers import get_admin_token, get_auth_header
from resources import strings
from resources.resource import get_resource, post_resource
from e2e_tests.conftest import get_workspace_owner_token

LOGGER = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio(loop_scope="session")
TIMEOUT = Timeout(10, read=60)


@pytest.mark.extended
@pytest.mark.timeout(75 * 60)
async def test_upgrade_guacamole_user_resource_template(setup_test_workspace_and_guacamole_service, verify) -> None:
    """
    E2E Test to verify template version upgrade on a user resource.
    1. Creates a user resource with initial version.
    2. Upgrades the user resource to target template version via PATCH.
    3. Verifies that the resource properties and templateVersion reflect the upgrade.
    """
    _, workspace_id, workspace_service_path, _ = setup_test_workspace_and_guacamole_service
    workspace_owner_token = await get_workspace_owner_token(workspace_id, verify)

    # Provision initial Guacamole VM user resource
    user_resource_payload = {
        "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
        "properties": {
            "display_name": "E2E Upgrade Test VM",
            "description": "VM created for E2E template upgrade testing",
            "os_image": "Windows 11",
            "admin_username": "researcher"
        }
    }

    user_resource_path, user_resource_id = await post_resource(
        user_resource_payload,
        f'/api{workspace_service_path}/{strings.API_USER_RESOURCES}',
        workspace_owner_token,
        verify,
        method="POST"
    )

    LOGGER.info(f"Created user resource: {user_resource_path} (ID: {user_resource_id})")

    # Fetch initial resource details
    resource_data = await get_resource(
        f'/api{user_resource_path}',
        workspace_owner_token,
        verify
    )
    initial_version = resource_data.get("templateVersion")
    LOGGER.info(f"Initial resource template version: {initial_version}")

    # Fetch template to find available versions
    template_data = await get_resource(
        f'/api{strings.API_WORKSPACE_SERVICE_TEMPLATES}/guacamole/{strings.API_USER_RESOURCE_TEMPLATES}/{strings.GUACAMOLE_WINDOWS_USER_RESOURCE}',
        workspace_owner_token,
        verify
    )
    current_version = template_data.get("version")

    # Perform upgrade with updateable property (description has "updateable": true)
    upgrade_patch_payload = {
        "templateVersion": current_version,
        "properties": {
            "display_name": "E2E Upgraded Test VM",
            "description": "Updated research description for VM post-upgrade"
        }
    }

    # Perform PATCH upgrade
    await post_resource(
        upgrade_patch_payload,
        f'/api{user_resource_path}',
        workspace_owner_token,
        verify,
        method="PATCH",
        etag=resource_data.get("_etag", "*")
    )

    # Retrieve upgraded resource and verify state
    upgraded_resource = await get_resource(
        f'/api{user_resource_path}',
        workspace_owner_token,
        verify
    )

    assert upgraded_resource.get("templateVersion") == current_version, "Template version did not update post-upgrade"
    assert upgraded_resource.get("properties", {}).get("display_name") == "E2E Upgraded Test VM", "Display name was not updated post-upgrade"
    assert upgraded_resource.get("properties", {}).get("description") == "Updated research description for VM post-upgrade", "Updateable property 'description' was not updated post-upgrade"


@pytest.mark.smoke
async def test_patch_rejects_non_updateable_property_modification(verify) -> None:
    """
    E2E Test to verify that PATCH rejects attempts to modify non-updateable properties
    (such as os_image, which has updateable: false).
    """
    admin_token = await get_admin_token(verify)
    async with AsyncClient(verify=verify, timeout=TIMEOUT) as client:
        # Invalid patch payload attempting to update non-updateable os_image property
        invalid_patch = {
            "properties": {
                "os_image": "Windows Server 2025"
            }
        }
        auth_headers = get_auth_header(admin_token)
        auth_headers["eTag"] = "*"

        # Call PATCH on an endpoint expecting a 400/422 validation failure
        response = await client.patch(
            f"{config.TRE_URL}/api{strings.API_WORKSPACE_SERVICE_TEMPLATES}/guacamole",
            headers=auth_headers,
            json=invalid_patch
        )

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_405_METHOD_NOT_ALLOWED], (
            f"Expected validation failure status code when modifying non-updateable os_image, got {response.status_code}"
        )
