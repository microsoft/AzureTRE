"""Exercise a private Gitea repository across an update and an app restart."""

import asyncio
from functools import partial
import logging
import os
from uuid import uuid4

import pytest

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.resources import strings
from e2e_tests.resources.gitea_probe import run_probe
from e2e_tests.resources.gitea_secrets import console_log_counts, key_vault_references
from e2e_tests.resources.resource import get_resource, post_resource
from e2e_tests.resources.sql_lifecycle import sql_lifecycle
from e2e_tests.resources.sql_probe import arm_client, COMPUTE_API, secret_access, validate_vm

LOGGER = logging.getLogger(__name__)
WEB_API = "2022-09-01"
MYSQL_API = "2023-12-30"
STORAGE_API = "2023-05-01"
GITEA_PAYLOAD = {
    "templateName": strings.GITEA_SERVICE,
    "properties": {
        "display_name": "Gitea lifecycle test",
        "description": "Private Gitea repository validation",
        "sql_sku": "B | 4GB 2vCores",
    },
}
VM_PAYLOAD = {
    "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
    "properties": {
        "display_name": "Gitea test client",
        "description": "Temporary private Gitea validation client",
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
@pytest.mark.gitea_validation
@pytest.mark.timeout(285 * 60)
async def test_private_gitea_repository_survives_update(verify):
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("The Gitea probe currently supports AzureCloud only")
    async with sql_lifecycle(verify, deadline_variable="GITEA_VALIDATION_DEADLINE") as resources:
        workspace_path, workspace_id, guacamole_path, guacamole_id = await resources.setup()
        token = await get_workspace_owner_token(workspace_id, verify)
        gitea_path, gitea_id = await resources.create(GITEA_PAYLOAD, f"/api{workspace_path}/workspace-services", token)
        vm_path, vm_id = await resources.create(VM_PAYLOAD, f"/api{guacamole_path}/user-resources", token)
        gitea = (await get_resource(f"/api{gitea_path}", token, verify))["workspaceService"]
        vm_properties = (await get_resource(f"/api{vm_path}", token, verify))["userResource"]["properties"]
        subscription_id = vm_properties.get("workspace_subscription_id") or os.environ["ARM_SUBSCRIPTION_ID"]
        suffix = f"{config.TRE_ID}-ws-{workspace_id[-4:]}-svc-{gitea_id[-4:]}"
        site = f"gitea-{suffix}"
        gitea_url = f"https://{site}.azurewebsites.net"
        assert gitea["properties"]["connection_uri"] == f"{gitea_url}/"
        vault = f"kv-{f'{config.TRE_ID}-ws-{workspace_id[-4:]}'[-20:]}".lower()
        azure_vm_id = vm_properties["azure_resource_id"]
        async with arm_client() as arm:
            vm = await arm.request("GET", azure_vm_id, COMPUTE_API)
            group = validate_vm(vm, azure_vm_id, subscription_id, config.TRE_ID, workspace_id, guacamole_id, vm_id)
            site_id = f"{group}/providers/Microsoft.Web/sites/{site}"
            storage_id = f"{group}/providers/Microsoft.Storage/storageAccounts/stgsvc{gitea_id[-4:]}"
            # Read the share through Resource Manager, because the storage firewall blocks the file endpoint.
            share = await arm.request("GET", f"{storage_id}/fileServices/default/shares/gitea-data", STORAGE_API)
            assert share["name"] == "gitea-data"
            probe_id = uuid4().hex
            secret_name = f"{site}-administrator-password"
            vault_id = f"{group}/providers/Microsoft.KeyVault/vaults/{vault}"
            async with secret_access(arm, vault_id, secret_name, vm["identity"]["principalId"], subscription_id):
                probe = partial(
                    run_probe,
                    arm,
                    azure_vm_id,
                    vm["location"],
                    gitea_url=gitea_url,
                    vault_name=vault,
                    secret_name=secret_name,
                    probe_id=probe_id,
                )
                await probe(phase="write")
                LOGGER.info("Gitea is private, rejects anonymous and wrong-password requests, and stores a commit")
                gitea = (await get_resource(f"/api{gitea_path}", token, verify))["workspaceService"]
                async with asyncio.timeout(60 * 60):
                    await post_resource(
                        {"properties": {"display_name": "Gitea lifecycle test (updated)"}},
                        f"/api{gitea_path}",
                        token,
                        verify,
                        method="PATCH",
                        etag=gitea["_etag"],
                    )
                # A restart makes the app read the repository from the file share and MySQL again.
                await arm.request("POST", f"{site_id}/restart", WEB_API)
                await probe(phase="read")
                LOGGER.info("The Gitea repository survived the update and the restart")
            # The web app sends its console log to Log Analytics, so the log must not show a secret.
            references = await key_vault_references(arm, site_id)
            assert set(references.values()) == {"Resolved"}, f"Gitea Key Vault references: {references}"
            log_workspace = (
                f"/subscriptions/{os.environ['ARM_SUBSCRIPTION_ID']}/resourceGroups/rg-{config.TRE_ID}"
                f"/providers/Microsoft.OperationalInsights/workspaces/log-{config.TRE_ID}"
            )
            counts = await console_log_counts(arm, log_workspace, site_id)
            LOGGER.info("Gitea console log lines: %s", counts)
            assert counts["leaks"] == 0, f"The Gitea console log has {counts['leaks']} lines with a secret"
            # Check the network settings last, so that a failure here keeps the functional evidence above.
            app = await arm.request("GET", site_id, WEB_API)
            server = await arm.request(
                "GET", f"{group}/providers/Microsoft.DBforMySQL/flexibleServers/mysql-{suffix}", MYSQL_API
            )
            storage = await arm.request("GET", storage_id, STORAGE_API)
            network = {
                "app": app["properties"].get("publicNetworkAccess"),
                "mysql": server["properties"]["network"].get("publicNetworkAccess"),
                "storage": storage["properties"]["networkAcls"].get("defaultAction"),
            }
            LOGGER.info("Gitea public network access: %s", network)
            expected = {"app": "Disabled", "mysql": "Disabled", "storage": "Deny"}
            assert network == expected, f"Gitea services allow public access: {network}"
