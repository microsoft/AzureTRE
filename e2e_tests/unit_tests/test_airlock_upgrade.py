"""Check the order and the checks of the Airlock upgrade cases without Azure."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import test_airlock_upgrade as upgrade
from e2e_tests.unit_tests.test_airlock_migration import token

WORKSPACE = "22222222-2222-4222-8222-222222222222"
PATH = f"/workspaces/{WORKSPACE}"


class UpgradeFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.events = []
        self.version = "2.10.1"
        self.airlock = 1
        self.seeds = []
        self.enterContext(
            patch.dict(
                os.environ,
                AZURE_ENVIRONMENT="AzureCloud",
                AIRLOCK_UPGRADE_VALIDATION_DEADLINE="",
                ARM_SUBSCRIPTION_ID="sub",
            )
        )
        for name, value in (
            ("TRE_ID", "tre-test"),
            ("TEST_WORKSPACE_APP_ID", "app"),
            ("TEST_WORKSPACE_APP_SECRET", "s"),
        ):
            self.enterContext(patch.object(upgrade.config, name, value))
        self.create = self.enterContext(
            patch.object(upgrade, "create_or_get_test_workspace", AsyncMock(return_value=(PATH, WORKSPACE)))
        )
        self.enterContext(
            patch.object(
                upgrade,
                "clean_up_test_workspace",
                AsyncMock(side_effect=lambda *a: self.events.append("delete-workspace")),
            )
        )
        owner = token(["WorkspaceOwner", "AirlockManager"])
        self.enterContext(patch.object(upgrade, "get_workspace_owner_token", AsyncMock(return_value=owner)))
        self.enterContext(patch.object(upgrade, "get_admin_token", AsyncMock(return_value="admin")))

        async def resource(endpoint, *args):
            if endpoint == "/api/workspaces":
                return {"workspaces": self.seeds}
            if endpoint == "/api/workspace-templates/tre-workspace-base":
                return {"version": "2.12.11"}
            properties = {"airlock_version": self.airlock}
            return {"workspace": {"_etag": "etag", "templateVersion": self.version, "properties": properties}}

        self.enterContext(patch.object(upgrade, "get_resource", resource))

        async def submit(*args):
            self.events.append("legacy-import")
            return f"legacy-{len(self.events)}", "https://stalimextretest.blob.core.windows.net/legacy?sig=x"

        self.enterContext(patch.object(upgrade, "submit_airlock_import_request", submit))

        async def draft(*args):
            self.events.append("draft-v2")
            return "new", "https://stalairlocktretest.blob.core.windows.net/new-draft?sig=x"

        self.enterContext(patch.object(upgrade, "create_draft_import_request_with_file", draft))

        async def post(payload, endpoint, *args):
            self.events.append(endpoint.rsplit("/", 1)[-1])
            return {}

        self.enterContext(patch.object(upgrade, "post_request", post))
        self.enterContext(
            patch.object(upgrade, "wait_for_status", AsyncMock(side_effect=lambda state, *a: self.events.append(state)))
        )

        async def request(endpoint, *args):
            if endpoint.endswith("/requests"):
                return {"airlockRequests": [{"airlockRequest": {"id": "legacy-0", "status": "approved"}}]}
            return {"airlockRequest": {"status": "approved", "airlock_version": 1}}

        self.enterContext(patch.object(upgrade, "get_request", request))

        async def core_accounts():
            self.events.append("core-accounts")
            return list(upgrade.CORE_LEGACY_ACCOUNTS)

        self.enterContext(patch.object(upgrade, "core_legacy_accounts", core_accounts))

        async def workspace_accounts(workspace_id):
            self.events.append(f"accounts-v{self.airlock}")
            return dict.fromkeys(upgrade.LEGACY_ACCOUNTS, "Deny" if self.airlock == 1 else None)

        self.enterContext(patch.object(upgrade, "legacy_accounts", workspace_accounts))

        async def change(payload, *args, **kwargs):
            if "templateVersion" in payload:
                self.events.append("upgrade")
                self.version = payload["templateVersion"]
            else:
                self.events.append("move-to-v2")
                self.airlock = payload["properties"]["airlock_version"]

        self.enterContext(patch.object(upgrade, "post_resource", change))

        async def patch_status(path, properties, *args):
            self.events.append(f"patch-v{properties['airlock_version']}")
            return 400

        self.enterContext(patch.object(upgrade, "patch_status", patch_status))

    async def test_seed_keeps_a_workspace_with_an_approved_legacy_import(self):
        await upgrade.test_seed_legacy_airlock_workspace(True)
        self.assertEqual(self.events, ["legacy-import", "review", "approved", "core-accounts", "accounts-v1"])
        self.assertEqual(
            self.create.await_args.kwargs["properties"], {"enable_airlock": True, "display_name": upgrade.SEED_NAME}
        )
        self.assertEqual(self.create.await_args.kwargs["auth_type"], "Manual")

    async def test_seed_refuses_a_second_seed(self):
        self.seeds = [{"id": WORKSPACE, "properties": {"display_name": upgrade.SEED_NAME}}]
        with self.assertRaisesRegex(ValueError, "already exists"):
            await upgrade.test_seed_legacy_airlock_workspace(True)
        self.create.assert_not_awaited()

    async def test_a_failed_seed_is_deleted(self):
        async def core_accounts():
            return []

        self.enterContext(patch.object(upgrade, "core_legacy_accounts", core_accounts))
        with self.assertRaises(AssertionError):
            await upgrade.test_seed_legacy_airlock_workspace(True)
        self.assertEqual(self.events[-1], "delete-workspace")

    async def test_verify_follows_the_documented_order(self):
        self.seeds = [{"id": WORKSPACE, "properties": {"display_name": upgrade.SEED_NAME}}]
        await upgrade.test_upgraded_legacy_workspace_moves_to_v2(True)
        self.assertEqual(
            self.events,
            [
                "core-accounts",
                "upgrade",
                "accounts-v1",
                "legacy-import",
                "review",
                "approved",
                "move-to-v2",
                "accounts-v2",
                "draft-v2",
                "cancel",
                "patch-v1",
                "delete-workspace",
            ],
        )

    async def test_verify_needs_the_seed(self):
        with self.assertRaisesRegex(ValueError, "airlock_upgrade_seed"):
            await upgrade.test_upgraded_legacy_workspace_moves_to_v2(True)

    async def test_an_upgrade_that_deletes_legacy_storage_fails_the_case(self):
        self.seeds = [{"id": WORKSPACE, "properties": {"display_name": upgrade.SEED_NAME}}]

        async def workspace_accounts(workspace_id):
            self.events.append("accounts")
            return dict.fromkeys(upgrade.LEGACY_ACCOUNTS)

        self.enterContext(patch.object(upgrade, "legacy_accounts", workspace_accounts))
        with self.assertRaises(AssertionError):
            await upgrade.test_upgraded_legacy_workspace_moves_to_v2(True)
        self.assertNotIn("move-to-v2", self.events)
        self.assertEqual(self.events[-1], "delete-workspace")


if __name__ == "__main__":
    unittest.main()
