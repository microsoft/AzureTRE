"""Check the order and the checks of the Porter upgrade cases without Azure."""

from contextlib import asynccontextmanager
import os
import unittest
from unittest.mock import AsyncMock, patch

from e2e_tests import test_porter_upgrade as upgrade

WORKSPACE = "33333333-3333-4333-8333-333333333333"
PATH = f"/workspaces/{WORKSPACE}"
SERVICE = f"{PATH}/workspace-services/service"
VMS = {
    upgrade.ACTION_VM: f"{SERVICE}/user-resources/action",
    upgrade.UNINSTALL_VM: f"{SERVICE}/user-resources/uninstall",
}
BLOCKED = f"Error message: Cannot run this action: {upgrade.UPGRADE_REQUIRED} can replace current values."


class PorterUpgradeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.events = []
        self.seeds = []
        self.upgraded = set()
        self.vm_exists = True
        self.enterContext(patch.dict(os.environ, PORTER_UPGRADE_VALIDATION_DEADLINE=""))
        for name, value in (("TEST_WORKSPACE_APP_ID", "app"), ("TEST_WORKSPACE_APP_SECRET", "s")):
            self.enterContext(patch.object(upgrade.config, name, value))
        self.create = self.enterContext(
            patch.object(upgrade, "create_or_get_test_workspace", AsyncMock(return_value=(PATH, WORKSPACE)))
        )
        self.enterContext(
            patch.object(
                upgrade,
                "create_or_get_test_workpace_service",
                AsyncMock(side_effect=lambda *a: self.events.append("service") or (SERVICE, "service")),
            )
        )
        self.enterContext(
            patch.object(
                upgrade,
                "clean_up_test_workspace",
                AsyncMock(side_effect=lambda *a: self.events.append("delete-workspace")),
            )
        )
        self.enterContext(patch.object(upgrade, "get_workspace_owner_token", AsyncMock(return_value="owner")))
        self.enterContext(patch.object(upgrade, "get_admin_token", AsyncMock(return_value="admin")))

        def vm(name, enabled):
            return {
                "resourcePath": VMS[name],
                "isEnabled": enabled,
                "templateVersion": "3.0.2",
                "properties": {"display_name": name, "azure_resource_id": f"/vm/{name}"},
            }

        async def resource(endpoint, *args):
            if endpoint == "/api/workspaces":
                return {"workspaces": self.seeds}
            if endpoint.endswith("/workspace-services"):
                return {
                    "workspaceServices": [
                        {"templateName": "tre-service-guacamole", "templateVersion": "0.14.4", "resourcePath": SERVICE}
                    ]
                }
            if endpoint.endswith("/user-resources"):
                return {"userResources": [vm(upgrade.ACTION_VM, True), vm(upgrade.UNINSTALL_VM, False)]}
            status = "updated" if endpoint.removeprefix("/api") in self.upgraded else "deployed"
            return {"userResource": {"templateVersion": "3.0.2", "_etag": "etag", "deploymentStatus": status}}

        self.enterContext(patch.object(upgrade, "get_resource", resource))

        async def post(payload, endpoint, *args, method="POST", **kwargs):
            if method == "POST":
                name = payload["properties"]["display_name"]
                self.events.append(f"create {name}")
                return VMS[name], name
            path = endpoint.removeprefix("/api")
            if payload == {"isEnabled": False}:
                self.events.append(f"disable {path}")
            else:
                self.assertEqual(payload, {"templateVersion": "3.0.2"})
                self.assertEqual(kwargs["etag"], "etag")
                self.events.append(f"upgrade {path}")
                self.upgraded.add(path)
            return path, path

        self.enterContext(patch.object(upgrade, "post_resource", post))

        async def action(path, name, *args):
            self.events.append(f"blocked-{name}" if path not in self.upgraded else name)
            if path in self.upgraded:
                return "action_succeeded", "done"
            return "action_failed", BLOCKED

        self.enterContext(patch.object(upgrade, "send_action", action))

        async def delete(path, *args):
            if path not in self.upgraded:
                self.events.append("blocked-delete")
                return "deleting_failed", BLOCKED
            self.events.append("delete")
            self.vm_exists = False
            return "deleted", "done"

        self.enterContext(patch.object(upgrade, "send_delete", delete))

        class Arm:
            async def request(arm, method, resource_id, api, missing_ok=False):
                self.events.append("vm-exists" if self.vm_exists else "vm-gone")
                return {} if self.vm_exists else None

        @asynccontextmanager
        async def arm_client():
            yield Arm()

        self.enterContext(patch.object(upgrade, "arm_client", arm_client))

    def seed(self):
        self.seeds = [{"id": WORKSPACE, "templateVersion": "2.10.1", "properties": {"display_name": upgrade.SEED_NAME}}]

    async def test_seed_keeps_two_vms_and_disables_one(self):
        await upgrade.test_seed_resources_with_legacy_overrides(True)
        self.assertEqual(
            self.events,
            [
                "service",
                f"create {upgrade.ACTION_VM}",
                f"create {upgrade.UNINSTALL_VM}",
                f"disable {VMS[upgrade.UNINSTALL_VM]}",
            ],
        )
        self.assertEqual(self.create.await_args.kwargs["properties"], {"display_name": upgrade.SEED_NAME})
        self.assertEqual(self.create.await_args.kwargs["auth_type"], "Manual")

    async def test_seed_refuses_a_second_seed(self):
        self.seed()
        with self.assertRaisesRegex(ValueError, "already exists"):
            await upgrade.test_seed_resources_with_legacy_overrides(True)
        self.create.assert_not_awaited()

    async def test_a_failed_seed_is_deleted(self):
        self.enterContext(patch.object(upgrade, "post_resource", AsyncMock(side_effect=AssertionError("failed"))))
        with self.assertRaises(AssertionError):
            await upgrade.test_seed_resources_with_legacy_overrides(True)
        self.assertEqual(self.events[-1], "delete-workspace")

    async def test_verify_follows_the_documented_order(self):
        self.seed()
        await upgrade.test_upgrade_clears_legacy_overrides(True)
        self.assertEqual(
            self.events,
            [
                "blocked-stop",
                "blocked-delete",
                "vm-exists",
                f"upgrade {VMS[upgrade.ACTION_VM]}",
                f"upgrade {VMS[upgrade.UNINSTALL_VM]}",
                "stop",
                "start",
                "delete",
                "vm-gone",
                "delete-workspace",
            ],
        )

    async def test_verify_needs_the_seed(self):
        with self.assertRaisesRegex(ValueError, "porter_upgrade_seed"):
            await upgrade.test_upgrade_clears_legacy_overrides(True)

    async def test_an_action_without_the_upgrade_message_fails_the_case(self):
        self.seed()
        for result in (("action_succeeded", "done"), ("action_failed", "Porter failed")):
            with self.subTest(result=result):
                self.events.clear()
                self.enterContext(patch.object(upgrade, "send_action", AsyncMock(return_value=result)))
                with self.assertRaises(AssertionError):
                    await upgrade.test_upgrade_clears_legacy_overrides(True)
                self.assertFalse([e for e in self.events if e.startswith("upgrade")])
                self.assertEqual(self.events[-1], "delete-workspace")

    async def test_an_uninstall_that_passes_with_overrides_fails_the_case(self):
        self.seed()
        self.enterContext(patch.object(upgrade, "send_delete", AsyncMock(return_value=("deleted", "done"))))
        with self.assertRaises(AssertionError):
            await upgrade.test_upgrade_clears_legacy_overrides(True)
        self.assertFalse([e for e in self.events if e.startswith("upgrade")])
        self.assertEqual(self.events[-1], "delete-workspace")


if __name__ == "__main__":
    unittest.main()
