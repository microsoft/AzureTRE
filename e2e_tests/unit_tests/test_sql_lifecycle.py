"""Exercise SQL lifecycle orchestration against the exposed VM API properties."""

from contextlib import asynccontextmanager
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import test_azuresql as sql
from e2e_tests.resources.sql_probe import SECRETS_USER
from e2e_tests.resources.sql_lifecycle import SQLResources


class SQLLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def run_lifecycle(self, workspace_subscription=None, *, unrelated_vm=False):
        workspace = ("/workspaces/ws1234", "ws1234", "/workspaces/ws1234/workspace-services/guac", "guac")
        subscription = workspace_subscription or "sub"
        group = f"/subscriptions/{subscription}/resourceGroups/rg-tre-test-ws-1234"
        vm_id = f"{group}/providers/Microsoft.Compute/virtualMachines/vm"
        properties = {"azure_resource_id": vm_id}
        if workspace_subscription is not None:
            properties["workspace_subscription_id"] = workspace_subscription
        server = "azsql-tre-test-ws-1234-svc-5678"
        vm = {
            "id": vm_id,
            "location": "switzerlandnorth",
            "identity": {"principalId": "principal"},
            "tags": {
                "tre_id": "tre-test",
                "tre_workspace_id": "another-workspace" if unrelated_vm else "ws1234",
                "tre_workspace_service_id": "guac",
                "tre_user_resource_id": "vm",
            },
        }
        arm = SimpleNamespace(
            request=AsyncMock(
                side_effect=[
                    vm,
                    {"properties": {"publicNetworkAccess": "Disabled", "minimalTlsVersion": "1.2"}},
                    {},
                ]
            ),
            delete=AsyncMock(),
        )
        resources = []

        async def record_cleanup(name):
            resources.append(name)

        async def resource(owner, payload, endpoint, token):
            name = "sql5678" if payload is sql.SQL_PAYLOAD else "vm"
            owner.own(name, record_cleanup, name)
            return f"{endpoint.removeprefix('/api')}/{name}", name

        @asynccontextmanager
        async def arm_client():
            yield arm

        with (
            patch.dict(os.environ, ARM_SUBSCRIPTION_ID="sub", AZURE_ENVIRONMENT="AzureCloud"),
            patch.object(sql.config, "TRE_ID", "tre-test"),
            patch.object(SQLResources, "create", resource),
            patch.object(SQLResources, "setup", AsyncMock(return_value=workspace)),
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
                        {"userResource": {"properties": properties}},
                    ]
                ),
            ),
            patch.object(sql, "arm_client", arm_client),
            patch.object(sql, "post_resource", AsyncMock()) as update,
            patch.object(sql, "run_probe", AsyncMock()) as probe,
        ):
            if unrelated_vm:
                with self.assertRaisesRegex(ValueError, "does not match the test-created resource"):
                    await sql.test_sql_query_survives_sku_upgrade(True)
                probe.assert_not_awaited()
                self.assertEqual(arm.request.await_count, 1)
                arm.delete.assert_not_awaited()
                self.assertEqual(resources, ["vm", "sql5678"])
                return
            await sql.test_sql_query_survives_sku_upgrade(True)
        self.assertEqual([call.kwargs["phase"] for call in probe.await_args_list], ["write", "read"])
        self.assertEqual([call.kwargs["expected_sku"] for call in probe.await_args_list], ["S1", "S2"])
        self.assertEqual({call.kwargs["vault_name"] for call in probe.await_args_list}, {"kv-tre-test-ws-1234"})
        self.assertEqual(arm.request.await_args_list[1].args[1], f"{group}/providers/Microsoft.Sql/servers/{server}")
        grant = arm.request.await_args_list[2]
        self.assertEqual(grant.args[0], "PUT")
        self.assertTrue(
            grant.args[1].startswith(
                f"{group}/providers/Microsoft.KeyVault/vaults/kv-tre-test-ws-1234/secrets/"
                f"{server}-administrator-password/providers/Microsoft.Authorization/roleAssignments/"
            )
        )
        self.assertEqual(
            grant.kwargs["body"]["properties"],
            {
                "roleDefinitionId": f"/subscriptions/{subscription}/providers/Microsoft.Authorization/roleDefinitions/{SECRETS_USER}",
                "principalId": "principal",
                "principalType": "ServicePrincipal",
            },
        )
        self.assertEqual(arm.delete.await_args.args[0], grant.args[1])
        self.assertEqual(update.call_args.args[0], {"properties": {"sql_sku": "S2 | 50 DTUs"}})
        self.assertEqual(resources, ["vm", "sql5678"])

    async def test_probes_use_workspace_vault_without_a_vm_keyvault_property(self):
        await self.run_lifecycle()

    async def test_workspace_subscription_selects_vm_and_secret_role(self):
        for subscription in ("", "sub", "workspace-sub"):
            with self.subTest(subscription=subscription):
                await self.run_lifecycle(subscription)

    async def test_unrelated_vm_is_rejected_before_granting_secret_access(self):
        await self.run_lifecycle("workspace-sub", unrelated_vm=True)
