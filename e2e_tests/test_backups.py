import uuid

import pytest
from starlette import status

from e2e_tests.helpers import assert_status, get_admin_token, get_template
from e2e_tests.resources import strings
from e2e_tests.resources.resource import get_resource, temporary_resource


pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.backups
@pytest.mark.parametrize(
    "enable_backup, expected_backup_outputs",
    [
        (True, True),
        (False, False),
    ],
)
async def test_create_base_workspace_with_backup_setting(enable_backup, expected_backup_outputs, verify) -> None:
    admin_token = await get_admin_token(verify=verify)

    async with get_template(strings.BASE_WORKSPACE, strings.API_WORKSPACE_TEMPLATES, admin_token, verify) as response:
        assert_status(response, [status.HTTP_200_OK], f"Failed to GET template: {strings.BASE_WORKSPACE}")
        template_properties = response.json().get("properties", {})
        assert "enable_backup" in template_properties

    properties = {
        "display_name": f"E2E Backup Workspace {uuid.uuid4().hex[:8]}",
        "description": "Base workspace for backup E2E tests",
        "auth_type": "Automatic",
        "address_space_size": "small",
        "enable_backup": enable_backup,
    }
    if enable_backup:
        properties["delete_backups_on_uninstall"] = True
    payload = {
        "templateName": strings.BASE_WORKSPACE,
        "properties": properties,
    }

    async with temporary_resource(payload, strings.API_WORKSPACES, admin_token, verify) as workspace_path:
        workspace = (await get_resource(f"/api{workspace_path}", admin_token, verify))["workspace"]

        assert workspace["deploymentStatus"] == strings.RESOURCE_STATUS_DEPLOYED

        properties = workspace.get("properties", {})
        backup_output_properties = [
            "backup_vault_name",
            "vm_backup_policy_id",
            "fileshare_backup_policy_id",
        ]

        for prop in backup_output_properties:
            value = properties.get(prop)
            if expected_backup_outputs:
                assert value, f"Expected non-empty workspace property '{prop}' when backup is enabled"
            else:
                assert not value, f"Expected empty workspace property '{prop}' when backup is disabled"
