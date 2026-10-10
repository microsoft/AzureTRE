"""Exercise SQL lifecycle orchestration against the exposed VM API properties."""

from contextlib import asynccontextmanager
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import test_azuresql as sql


class SQLLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_probes_use_workspace_vault_without_a_vm_keyvault_property(self):
        workspace = ("/workspaces/ws1234", "ws1234", "/workspaces/ws1234/workspace-services/guac", "guac")
        vm_id = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm"
        server = "azsql-tre-test-ws-1234-svc-5678"
        arm = SimpleNamespace(
            request=AsyncMock(
                side_effect=[
                    {"location": "switzerlandnorth", "identity": {"principalId": "principal"}},
                    {"properties": {"publicNetworkAccess": "Disabled", "minimalTlsVersion": "1.2"}},
                ]
            )
        )
        grants = []
        resources = []

        @asynccontextmanager
        async def resource(payload, endpoint, token, verify):
            name = "sql5678" if payload is sql.SQL_PAYLOAD else "vm"
            try:
                yield f"{endpoint.removeprefix('/api')}/{name}", name
            finally:
                resources.append(name)

        @asynccontextmanager
        async def arm_client():
            yield arm

        @asynccontextmanager
        async def access(*args):
            grants.append(args)
            yield

        with (
            patch.dict(os.environ, ARM_SUBSCRIPTION_ID="sub", AZURE_ENVIRONMENT="AzureCloud"),
            patch.object(sql.config, "TRE_ID", "tre-test"),
            patch.object(sql, "managed_test_resource", resource),
            patch.object(sql, "get_workspace_owner_token", AsyncMock(return_value="token")),
            patch.object(
                sql,
                "get_resource",
                AsyncMock(
                    side_effect=[
                        {
                            "workspaceService": {
                                "properties": {"azuresql_fqdn": f"{server}.database.windows.net"},
                                "_etag": "etag",
                            }
                        },
                        {"userResource": {"properties": {"azure_resource_id": vm_id}}},
                    ]
                ),
            ),
            patch.object(sql, "arm_client", arm_client),
            patch.object(sql, "validate_vm", return_value="/subscriptions/sub/resourceGroups/rg"),
            patch.object(sql, "secret_access", access),
            patch.object(sql, "post_resource", AsyncMock()) as update,
            patch.object(sql, "run_probe", AsyncMock()) as probe,
        ):
            await sql.test_sql_query_survives_sku_upgrade(workspace, True)
        self.assertEqual([call.kwargs["phase"] for call in probe.await_args_list], ["write", "read"])
        self.assertEqual([call.kwargs["expected_sku"] for call in probe.await_args_list], ["S1", "S2"])
        self.assertEqual({call.kwargs["vault_name"] for call in probe.await_args_list}, {"kv-tre-test-ws-1234"})
        self.assertTrue(grants[0][1].endswith("/vaults/kv-tre-test-ws-1234"))
        self.assertEqual(update.call_args.args[0], {"properties": {"sql_sku": "S2 | 50 DTUs"}})
        self.assertEqual(resources, ["vm", "sql5678"])
