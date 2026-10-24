"""Back up and restore known data on the workspace file share, then delete the workspace with each backup choice."""

from functools import partial
import logging
import os
from uuid import uuid4

from httpx import AsyncClient
import pytest
from starlette import status

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.helpers import get_admin_token, get_auth_header, get_full_endpoint
from e2e_tests.resources import strings
from e2e_tests.resources.backup import (
    BACKUP_API,
    FILE_DATA_PRIVILEGED_CONTRIBUTOR,
    GROUP_API,
    SHARE,
    STORAGE_API,
    back_up_now,
    names,
    protected_share,
    recovery_points,
    remove_retained_backup,
    restore_file,
)
from e2e_tests.resources.backup_probe import run_probe
from e2e_tests.resources.health_probe import role_access
from e2e_tests.resources.resource import get_resource
from e2e_tests.resources.sql_lifecycle import sql_lifecycle
from e2e_tests.resources.sql_probe import arm_client, COMPUTE_API, validate_vm

LOGGER = logging.getLogger(__name__)
VM_PAYLOAD = {
    "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
    "properties": {
        "display_name": "Backup test client",
        "description": "Temporary file share backup validation client",
        "os_image": "Windows 11",
        "vm_size": "2 CPU | 8GB RAM",
        "admin_username": "researcher",
        "shared_storage_access": False,
        **{
            f"install_{tool}": False
            for tool in ("azure_cli", "vscode", "storage_explorer", "git", "python_tools", "r_tools")
        },
    },
}


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.backup_validation
@pytest.mark.timeout(285 * 60)
@pytest.mark.parametrize(
    "delete_backups",
    [
        pytest.param(False, id="retain", marks=pytest.mark.backup_retention),
        pytest.param(True, id="delete", marks=pytest.mark.backup_deletion),
    ],
)
async def test_file_share_restore_and_workspace_delete(verify, delete_backups):
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("The backup probe currently supports AzureCloud only")
    properties = {"enable_backup": True, "delete_backups_on_uninstall": delete_backups}
    async with sql_lifecycle(verify, deadline_variable="BACKUP_VALIDATION_DEADLINE") as resources:
        workspace_path, workspace_id, guacamole_path, guacamole_id = await resources.setup(
            workspace_properties=properties
        )
        new_token = partial(get_workspace_owner_token, workspace_id, verify)
        workspace = (await get_resource(f"/api{workspace_path}", await new_token(), verify))["workspace"]
        subscription_id = workspace["properties"].get("workspace_subscription_id") or os.environ["ARM_SUBSCRIPTION_ID"]
        resource_names = names(workspace_id, config.TRE_ID)
        group_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_names['group']}"
        vault_id = f"{group_id}/providers/Microsoft.RecoveryServices/vaults/{resource_names['vault']}"
        account_id = f"{group_id}/providers/Microsoft.Storage/storageAccounts/{resource_names['account']}"
        # This runs after the workspace delete, also when the case fails before it.
        resources.own_last(
            "retained backup", remove_kept_backup, workspace_path, group_id, vault_id, account_id, verify
        )
        vm_path, vm_id = await resources.create(
            VM_PAYLOAD, f"/api{guacamole_path}/user-resources", await new_token(), cleanup_token=new_token
        )
        vm_properties = (await get_resource(f"/api{vm_path}", await new_token(), verify))["userResource"]["properties"]
        azure_vm_id = vm_properties["azure_resource_id"]
        probe_id = uuid4().hex
        async with arm_client() as arm:
            vm = await arm.request("GET", azure_vm_id, COMPUTE_API)
            validate_vm(vm, azure_vm_id, subscription_id, config.TRE_ID, workspace_id, guacamole_id, vm_id)
            probe = partial(
                run_probe,
                arm,
                azure_vm_id,
                vm["location"],
                account=resource_names["account"],
                share=SHARE,
                probe_id=probe_id,
            )
            await probe(phase="access")
            item_id = (await protected_share(arm, vault_id))["id"]
            # Azure Backup puts a delete lock on the storage account. The lock also blocks the delete of a
            # role assignment on the account or the share, so the temporary role is on the resource group.
            async with role_access(
                arm, group_id, FILE_DATA_PRIVILEGED_CONTRIBUTOR, vm["identity"]["principalId"], subscription_id
            ):
                await probe(phase="write")
                await back_up_now(arm, vault_id, item_id)
                point = (await recovery_points(arm, item_id))[-1]
                LOGGER.info("Azure Backup made recovery point %s of the file share", point["name"])
                await probe(phase="change")
                await restore_file(arm, vault_id, item_id, point["name"], account_id, f"e2e-{probe_id}.txt")
                await probe(phase="read")
                LOGGER.info("The restore put the backed-up file back on the share")

            await resources.delete_now(vm_path)
            await resources.delete_now(guacamole_path)
            await resources.delete_now(workspace_path)
            LOGGER.info("The workspace delete passed with delete_backups_on_uninstall=%s", delete_backups)

            group = await arm.request("GET", group_id, GROUP_API, missing_ok=True)
            if delete_backups:
                assert group is None, "The workspace resource group is still there after a delete with the backups"
                return
            assert group is not None, "The retained resource group is missing"
            item = await arm.request("GET", item_id, BACKUP_API)
            assert item["properties"]["protectionState"] == "ProtectionStopped"
            assert await recovery_points(arm, item_id), "The retained item has no recovery point"
            account = await arm.request("GET", account_id, STORAGE_API)
            assert account["properties"]["networkAcls"]["defaultAction"] == "Deny"
            await arm.request("GET", f"{account_id}/fileServices/default/shares/{SHARE}", STORAGE_API)
            # The recovery point must still work after the workspace is gone.
            await restore_file(arm, vault_id, item_id, point["name"], account_id, f"e2e-{probe_id}.txt")
            LOGGER.info("The retained recovery point restored after the workspace delete")


async def remove_kept_backup(workspace_path, group_id, vault_id, account_id, verify):
    """Remove the vault and the resource group that a delete with retained backups keeps."""
    # A workspace that the API did not delete stays as it is, so that its failure can be examined.
    async with AsyncClient(verify=verify, timeout=60) as client:
        response = await client.get(
            get_full_endpoint(f"/api{workspace_path}"), headers=get_auth_header(await get_admin_token(verify))
        )
    if response.status_code != status.HTTP_404_NOT_FOUND:
        LOGGER.warning("The workspace is not deleted (HTTP %s), so its backup resources stay", response.status_code)
        return
    async with arm_client() as arm:
        await remove_retained_backup(arm, group_id, vault_id, account_id)
