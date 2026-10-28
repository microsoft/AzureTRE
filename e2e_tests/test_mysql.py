"""Exercise MySQL data access and a supported SKU change privately."""

import asyncio
import logging
import os
from uuid import uuid4

import pytest

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.resources import strings
from e2e_tests.resources.mysql_probe import run_probe
from e2e_tests.resources.nexus import nexus_prerequisites
from e2e_tests.resources.resource import get_resource, post_resource
from e2e_tests.resources.sql_lifecycle import sql_lifecycle
from e2e_tests.resources.sql_probe import arm_client, COMPUTE_API, secret_access, validate_vm

LOGGER = logging.getLogger(__name__)
MYSQL_API = "2023-12-30"
DATABASE = "tredb"
MYSQL_PAYLOAD = {
    "templateName": strings.MYSQL_SERVICE,
    "properties": {
        "display_name": "MySQL lifecycle test",
        "description": "Private MySQL query and SKU change validation",
        "sql_sku": "B | 4GB 2vCores",
        "db_name": DATABASE,
    },
}
VM_PAYLOAD = {
    "templateName": strings.GUACAMOLE_LINUX_USER_RESOURCE,
    "properties": {
        "display_name": "MySQL test client",
        "description": "Temporary private MySQL validation client",
        "os_image": "Ubuntu 22.04 LTS",
        "vm_size": "2 CPU | 8GB RAM",
        # CI uses a service principal, so the bundle cannot derive a username from its owner.
        "admin_username": "researcher",
    },
}
SKUS = {"B | 4GB 2vCores": "Standard_B2s", "GP | 8GB 2vCores": "Standard_D2ds_v4"}


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.mysql_validation
@pytest.mark.timeout(285 * 60)
async def test_private_mysql_query_survives_sku_change(verify):
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("The MySQL probe currently supports AzureCloud only")
    async with sql_lifecycle(verify, deadline_variable="MYSQL_VALIDATION_DEADLINE") as resources:
        workspace_path, workspace_id, guacamole_path, guacamole_id = await resources.setup()
        # The Linux VM installs its packages through Nexus.
        async with asyncio.timeout(60 * 60):
            await resources.enter("Nexus prerequisites", nexus_prerequisites(verify))
        token = await get_workspace_owner_token(workspace_id, verify)
        mysql_path, mysql_id = await resources.create(MYSQL_PAYLOAD, f"/api{workspace_path}/workspace-services", token)
        vm_path, vm_id = await resources.create(VM_PAYLOAD, f"/api{guacamole_path}/user-resources", token)
        mysql = (await get_resource(f"/api{mysql_path}", token, verify))["workspaceService"]
        vm_properties = (await get_resource(f"/api{vm_path}", token, verify))["userResource"]["properties"]
        subscription_id = vm_properties.get("workspace_subscription_id") or os.environ["ARM_SUBSCRIPTION_ID"]
        server = f"mysql-{config.TRE_ID}-ws-{workspace_id[-4:]}-svc-{mysql_id[-4:]}"
        assert mysql["properties"]["mysql_fqdn"] == f"{server}.mysql.database.azure.com"
        vault = f"kv-{f'{config.TRE_ID}-ws-{workspace_id[-4:]}'[-20:]}".lower()
        azure_vm_id = vm_properties["azure_resource_id"]
        async with arm_client() as arm:
            vm = await arm.request("GET", azure_vm_id, COMPUTE_API)
            group = validate_vm(vm, azure_vm_id, subscription_id, config.TRE_ID, workspace_id, guacamole_id, vm_id)
            server_id = f"{group}/providers/Microsoft.DBforMySQL/flexibleServers/{server}"
            server_record = await arm.request("GET", server_id, MYSQL_API)
            assert server_record["sku"]["name"] == SKUS["B | 4GB 2vCores"]
            assert server_record["properties"]["network"]["publicNetworkAccess"] == "Disabled"
            secure = await arm.request("GET", f"{server_id}/configurations/require_secure_transport", MYSQL_API)
            assert secure["properties"]["value"].upper() == "ON"
            vault_id = f"{group}/providers/Microsoft.KeyVault/vaults/{vault}"
            secret_name = f"{server}-administrator-password"
            probe_id = uuid4().hex
            async with secret_access(arm, vault_id, secret_name, vm["identity"]["principalId"], subscription_id):
                probe = dict(
                    server=f"{server}.mysql.database.azure.com",
                    vault_name=vault,
                    secret_name=secret_name,
                    database=DATABASE,
                    probe_id=probe_id,
                )
                await run_probe(arm, azure_vm_id, vm["location"], **probe, phase="write")
                LOGGER.info("MySQL query passed through private DNS on the Burstable SKU")
                mysql = (await get_resource(f"/api{mysql_path}", token, verify))["workspaceService"]
                async with asyncio.timeout(60 * 60):
                    await post_resource(
                        {"properties": {"sql_sku": "GP | 8GB 2vCores"}},
                        f"/api{mysql_path}",
                        token,
                        verify,
                        method="PATCH",
                        etag=mysql["_etag"],
                    )
                server_record = await arm.request("GET", server_id, MYSQL_API)
                assert server_record["sku"]["name"] == SKUS["GP | 8GB 2vCores"]
                # The SKU change must keep the network and TLS settings.
                assert server_record["properties"]["network"]["publicNetworkAccess"] == "Disabled"
                secure = await arm.request("GET", f"{server_id}/configurations/require_secure_transport", MYSQL_API)
                assert secure["properties"]["value"].upper() == "ON"
                await run_probe(arm, azure_vm_id, vm["location"], **probe, phase="read")
                LOGGER.info("MySQL data survived the change to the General Purpose SKU")
