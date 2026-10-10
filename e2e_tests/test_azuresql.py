"""Exercise SQL data access and a supported configuration upgrade privately."""

import asyncio
from contextlib import asynccontextmanager
import logging
import os
from uuid import uuid4

import pytest

from e2e_tests import config
from e2e_tests.conftest import get_workspace_owner_token
from e2e_tests.resources import strings
from e2e_tests.resources.resource import disable_and_delete_resource, get_resource, post_resource
from e2e_tests.resources.sql_probe import arm_client, COMPUTE_API, run_probe, secret_access, validate_vm

LOGGER = logging.getLogger(__name__)
TERMINAL_STATES = {
    "deployed",
    "deployment_failed",
    "updated",
    "updating_failed",
    "deleted",
    "deleting_failed",
    "action_succeeded",
    "action_failed",
    "pipeline_succeeded",
    "pipeline_failed",
}
SQL_PAYLOAD = {
    "templateName": strings.AZURESQL_SERVICE,
    "properties": {
        "display_name": "SQL lifecycle test",
        "description": "Private SQL query and SKU upgrade validation",
        "sql_sku": "S1 | 20 DTUs",
        "db_name": "tredb",
    },
}
VM_PAYLOAD = {
    "templateName": strings.GUACAMOLE_WINDOWS_USER_RESOURCE,
    "properties": {
        "display_name": "SQL test client",
        "description": "Temporary private SQL validation client",
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


@asynccontextmanager
async def managed_test_resource(payload, endpoint, token, verify):
    async with asyncio.timeout(60 * 60):
        resource_path, resource_id = await post_resource(payload, endpoint, token, verify, cleanup_failed_create=True)
    original = None
    try:
        yield resource_path, resource_id
    except BaseException as error:
        original = error
        raise
    finally:
        try:
            async with asyncio.timeout(60 * 60):
                while True:
                    operations = (await get_resource(f"/api{resource_path}/operations", token, verify))["operations"]
                    if all(op["status"] in TERMINAL_STATES for op in operations):
                        break
                    await asyncio.sleep(30)
                await disable_and_delete_resource(f"/api{resource_path}", token, verify, allow_failed_disable=True)
        except Exception as cleanup_error:
            if original is None:
                raise
            original.add_note(f"Cleanup of {resource_path} also failed: {cleanup_error!r}")


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.sql_validation
@pytest.mark.timeout(4 * 60 * 60)
async def test_sql_query_survives_sku_upgrade(setup_test_workspace_and_guacamole_service, verify):
    if os.environ.get("AZURE_ENVIRONMENT", "AzureCloud") != "AzureCloud":
        raise ValueError("The SQL probe currently supports AzureCloud only")
    subscription_id = os.environ["ARM_SUBSCRIPTION_ID"]
    workspace_path, workspace_id, guacamole_path, guacamole_id = setup_test_workspace_and_guacamole_service
    token = await get_workspace_owner_token(workspace_id, verify)
    async with managed_test_resource(SQL_PAYLOAD, f"/api{workspace_path}/workspace-services", token, verify) as (
        sql_path,
        sql_id,
    ):
        async with managed_test_resource(VM_PAYLOAD, f"/api{guacamole_path}/user-resources", token, verify) as (
            vm_path,
            vm_id,
        ):
            sql = (await get_resource(f"/api{sql_path}", token, verify))["workspaceService"]
            vm_properties = (await get_resource(f"/api{vm_path}", token, verify))["userResource"]["properties"]
            server = f"azsql-{config.TRE_ID}-ws-{workspace_id[-4:]}-svc-{sql_id[-4:]}"
            assert sql["properties"]["azuresql_fqdn"] == f"{server}.database.windows.net"
            vault = f"kv-{f'{config.TRE_ID}-ws-{workspace_id[-4:]}'[-20:]}"
            assert vm_properties["keyvault_name"] == vault
            azure_vm_id = vm_properties["azure_resource_id"]
            async with arm_client() as arm:
                vm = await arm.request("GET", azure_vm_id, COMPUTE_API)
                group = validate_vm(vm, azure_vm_id, subscription_id, config.TRE_ID, workspace_id, guacamole_id, vm_id)
                sql_server = await arm.request("GET", f"{group}/providers/Microsoft.Sql/servers/{server}", "2023-08-01")
                assert sql_server["properties"]["publicNetworkAccess"] == "Disabled"
                assert sql_server["properties"]["minimalTlsVersion"] == "1.2"
                vault_id = f"{group}/providers/Microsoft.KeyVault/vaults/{vault}"
                secret_name = f"{server}-administrator-password"
                probe_id = uuid4().hex
                async with secret_access(arm, vault_id, secret_name, vm["identity"]["principalId"], subscription_id):
                    probe = dict(
                        server=f"{server}.database.windows.net",
                        vault_name=vault,
                        secret_name=secret_name,
                        probe_id=probe_id,
                    )
                    await run_probe(arm, azure_vm_id, vm["location"], **probe, phase="write", expected_sku="S1")
                    LOGGER.info("SQL query passed through private DNS at S1")
                    async with asyncio.timeout(60 * 60):
                        await post_resource(
                            {"properties": {"sql_sku": "S2 | 50 DTUs"}},
                            f"/api{sql_path}",
                            token,
                            verify,
                            method="PATCH",
                            etag=sql["_etag"],
                        )
                    await run_probe(arm, azure_vm_id, vm["location"], **probe, phase="read", expected_sku="S2")
                    LOGGER.info("SQL data survived the S1-to-S2 configuration upgrade")
