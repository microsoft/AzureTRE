"""Check the file share backup probe, the Azure Backup helpers and the backup case set-up."""

import json
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from jsonschema import validate

from api_app.services.schema_service import enrich_user_resource_template
from e2e_tests import test_backup_restore as case
from e2e_tests.resources import backup
from e2e_tests.resources import backup_probe as probe
from e2e_tests.resources import sql_lifecycle

ROOT = Path(__file__).resolve().parents[2]
VAULT = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd/providers/Microsoft.RecoveryServices/vaults/arsv-tre-ws-abcd"
ITEM = f"{VAULT}/backupFabrics/Azure/protectionContainers/StorageContainer;storage;rg;stgwsabcd/protectedItems/AzureFileShare;x"
PROBE_ID = "0123456789abcdef0123456789abcdef"


def result(evidence, state="Succeeded", code=0, output=None):
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "instanceView": {
                "executionState": state,
                "exitCode": code,
                "output": output if output is not None else "BACKUP_PROBE_RESULT=" + json.dumps(evidence),
            },
        }
    }


class ProbeTests(unittest.TestCase):
    def test_access_needs_a_denied_request_and_data_phases_need_the_expected_file(self):
        access = probe.expected_result("access", PROBE_ID)
        self.assertEqual(access["unassigned"], 403)
        self.assertTrue(probe.probe_result(result(access), "access", PROBE_ID))
        with self.assertRaises(AssertionError):
            probe.probe_result(result({**access, "unassigned": 200}), "access", PROBE_ID)
        for phase in ("write", "change", "read"):
            evidence = probe.expected_result(phase, PROBE_ID)
            with self.subTest(phase=phase):
                self.assertTrue(probe.probe_result(result(evidence), phase, PROBE_ID))
                for change in ({"matches": False}, {"private_dns": False}):
                    with self.assertRaises(AssertionError):
                        probe.probe_result(result({**evidence, **change}), phase, PROBE_ID)

    def test_running_command_is_not_a_pass_and_failure_names_the_stage(self):
        running = result({})
        running["properties"]["instanceView"] = {}
        self.assertFalse(probe.probe_result(running, "write", PROBE_ID))
        failed = result({}, state="Failed", code=1, output="BACKUP_PROBE_FAILED=file-role\n")
        with self.assertRaisesRegex(AssertionError, "stage=file-role"):
            probe.probe_result(failed, "write", PROBE_ID)

    def test_script_accepts_the_names_that_the_case_builds(self):
        found = re.findall(r"ValidatePattern\('([^']+)'\)\]\[string\]\$(\w+)", probe.SCRIPT.read_text())
        patterns = {name: pattern for pattern, name in found}
        self.assertRegex(backup.names("0123-abcd", "tre")["account"], patterns["Account"])
        self.assertRegex(backup.SHARE, patterns["Share"])
        self.assertRegex(PROBE_ID, patterns["ProbeId"])

    def test_names_follow_the_base_workspace(self):
        self.assertEqual(
            backup.names("00000000-0000-0000-0000-00000000abcd", "tre"),
            {"group": "rg-tre-ws-abcd", "vault": "arsv-tre-ws-abcd", "account": "stgwsabcd"},
        )
        locals_tf = (ROOT / "templates/workspaces/base/terraform/locals.tf").read_text()
        self.assertIn('shared_storage_name       = "vm-shared-storage"', locals_tf)

    def test_vm_payload_matches_the_enriched_api_schema(self):
        schema = json.loads(
            (
                ROOT
                / "templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm/template_schema.json"
            ).read_text()
        )
        validate(
            case.VM_PAYLOAD["properties"], enrich_user_resource_template(SimpleNamespace(model_dump=lambda **_: schema))
        )


class FakeResponse:
    def __init__(self, status_code, body=None, headers=None):
        self.status_code = status_code
        self._body = body or {}
        self.headers = headers or {}

    def json(self):
        return self._body


def fake_arm(post=None, get=None, request=None):
    credential = SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token"))
    client = SimpleNamespace(post=AsyncMock(return_value=post), get=AsyncMock(side_effect=get or []))
    return SimpleNamespace(client=client, credential=credential, request=AsyncMock(side_effect=request))


class AzureBackupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        sleep = patch.object(backup.asyncio, "sleep", AsyncMock())
        sleep.start()
        self.addCleanup(sleep.stop)

    async def test_a_request_returns_the_job_that_azure_backup_starts(self):
        arm = fake_arm(
            post=FakeResponse(202, headers={"Azure-AsyncOperation": "https://status"}),
            get=[
                FakeResponse(200, {"status": "InProgress"}),
                FakeResponse(200, {"status": "Succeeded", "properties": {"jobId": "job-1"}}),
            ],
        )
        self.assertEqual(await backup.start_job(arm, f"{ITEM}/backup", {}), "job-1")
        self.assertEqual(arm.client.post.await_args.kwargs["params"], {"api-version": backup.BACKUP_API})

    async def test_a_request_that_starts_no_job_fails(self):
        for post, get in (
            (FakeResponse(400), []),
            (FakeResponse(202, headers={"Location": "https://status"}), [FakeResponse(200, {"status": "Failed"})]),
        ):
            with self.subTest(status=post.status_code), self.assertRaises((RuntimeError, AssertionError)):
                await backup.start_job(fake_arm(post=post, get=get), f"{ITEM}/backup", {})

    async def test_only_a_completed_job_passes(self):
        def job(state):
            return {"properties": {"status": state}}

        arm = fake_arm(request=[job("InProgress"), job("Completed")])
        await backup.wait_for_job(arm, VAULT, "job-1")
        self.assertEqual(arm.request.await_count, 2)
        for state in ("Failed", "CompletedWithWarnings", "Cancelled"):
            with self.subTest(state=state), self.assertRaisesRegex(AssertionError, state):
                await backup.wait_for_job(fake_arm(request=[job(state)]), VAULT, "job-1")

    async def test_the_protected_item_is_the_shared_file_share(self):
        # Azure Backup returns IDs that start with /Subscriptions/.
        items = {
            "value": [
                {"id": "/Subscriptions/sub/other", "properties": {"friendlyName": "other"}},
                {
                    "id": "/Subscriptions/" + ITEM.removeprefix("/subscriptions/"),
                    "properties": {"friendlyName": backup.SHARE},
                },
            ]
        }
        self.assertEqual((await backup.protected_share(fake_arm(request=[items]), VAULT))["id"], ITEM)
        with self.assertRaises(AssertionError):
            await backup.protected_share(fake_arm(request=[{"value": []}]), VAULT)

    async def test_a_restore_puts_one_file_back_in_its_original_place(self):
        with (
            patch.object(backup, "start_job", AsyncMock(return_value="job-2")) as start,
            patch.object(backup, "wait_for_job", AsyncMock()) as wait,
        ):
            await backup.restore_file(MagicMock(), VAULT, ITEM, "point-1", "/account", "e2e.txt")
        path, body = start.await_args.args[1:]
        self.assertEqual(path, f"{ITEM}/recoveryPoints/point-1/restore")
        self.assertEqual(body["properties"]["recoveryType"], "OriginalLocation")
        self.assertEqual(body["properties"]["restoreFilePaths"], [{"path": "e2e.txt", "fileSpecType": "File"}])
        wait.assert_awaited_once_with(unittest.mock.ANY, VAULT, "job-2")

    async def test_the_retained_vault_is_removed_with_soft_delete_off_first(self):
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        calls = []

        async def request(method, resource_id, api_version, **kwargs):
            calls.append((method, resource_id))
            if method != "GET":
                return {}
            if resource_id.endswith("/locks"):
                return {"value": [{"id": f"{group}/providers/Microsoft.Authorization/locks/backup"}]}
            if resource_id.endswith("/backupProtectedItems"):
                return {"value": [{"id": "/Subscriptions/" + ITEM.removeprefix("/subscriptions/"), "properties": {}}]}
            # The group and the vault exist before their delete. Each wait sees the resource gone.
            deleted = {resource for verb, resource in calls if verb == "DELETE"}
            return None if resource_id in deleted else {}

        await backup.remove_retained_backup(fake_arm(request=request), group, VAULT)
        deletes = [resource for method, resource in calls if method == "DELETE"]
        self.assertEqual(calls[2], ("PATCH", f"{VAULT}/backupconfig/vaultconfig"))
        self.assertEqual(
            deletes,
            [
                ITEM,
                ITEM.split("/protectedItems/")[0],
                VAULT,
                f"{group}/providers/Microsoft.Authorization/locks/backup",
                group,
            ],
        )

    async def test_nothing_is_removed_when_the_resource_group_is_gone(self):
        arm = fake_arm(request=[None])
        await backup.remove_retained_backup(arm, "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd", VAULT)
        self.assertEqual(arm.request.await_count, 1)


class KeptBackupCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_kept_backup_is_removed_only_after_the_api_deleted_the_workspace(self):
        for code, removed in ((404, True), (200, False)):
            client = MagicMock()
            client.__aenter__ = AsyncMock(return_value=SimpleNamespace(get=AsyncMock(return_value=FakeResponse(code))))
            client.__aexit__ = AsyncMock(return_value=False)
            arm = MagicMock()
            arm.__aenter__ = AsyncMock(return_value="arm")
            arm.__aexit__ = AsyncMock(return_value=False)
            with (
                self.subTest(code=code),
                patch.object(case, "AsyncClient", return_value=client),
                patch.object(case, "get_admin_token", AsyncMock(return_value="token")),
                patch.object(case, "arm_client", return_value=arm),
                patch.object(case, "remove_retained_backup", AsyncMock()) as remove,
            ):
                await case.remove_kept_backup("/workspaces/w", "/group", VAULT, True)
            if removed:
                remove.assert_awaited_once_with("arm", "/group", VAULT)
            else:
                remove.assert_not_awaited()


class BackupSetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_case_with_workspace_settings_gets_its_own_automatic_workspace(self):
        resources = sql_lifecycle.SQLResources(False, 0)
        with (
            patch.object(sql_lifecycle.config, "TEST_WORKSPACE_APP_ID", "app"),
            patch.object(sql_lifecycle.config, "TEST_WORKSPACE_ID", "existing"),
            patch.object(
                sql_lifecycle, "create_or_get_test_workspace", AsyncMock(return_value=("/workspaces/w", "w"))
            ) as create,
            patch.object(sql_lifecycle, "get_workspace_owner_token", AsyncMock(return_value="token")),
            patch.object(sql_lifecycle, "create_or_get_test_workpace_service", AsyncMock(return_value=("/s", "s"))),
        ):
            await resources.setup(workspace_properties={"enable_backup": True})
        kwargs = create.await_args.kwargs
        self.assertEqual(kwargs["auth_type"], "Automatic")
        self.assertEqual(kwargs["pre_created_workspace_id"], "")
        self.assertEqual(kwargs["properties"], {"enable_backup": True})

    async def test_delete_now_runs_one_cleanup_and_removes_it(self):
        resources = sql_lifecycle.SQLResources(False, 0)
        first, second = AsyncMock(), AsyncMock()
        resources.own("/one", first)
        resources.own("/two", second)
        await resources.delete_now("/one")
        first.assert_awaited_once()
        second.assert_not_awaited()
        self.assertEqual([name for name, _ in resources.finalisers], ["/two"])

    async def test_a_last_cleanup_runs_after_the_cleanups_owned_before_it(self):
        resources = sql_lifecycle.SQLResources(False, sql_lifecycle.asyncio.get_running_loop().time() + 60)
        order = []

        def record(name):
            return AsyncMock(side_effect=lambda: order.append(name))

        resources.own("/workspace", record("/workspace"))
        resources.own_last("retained backup", record("retained backup"))
        resources.own("/vm", record("/vm"))
        self.assertEqual(await resources.close(), [])
        self.assertEqual(order, ["/vm", "/workspace", "retained backup"])


class WorkspacePayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_case_settings_replace_the_backup_default(self):
        from contextlib import asynccontextmanager

        from e2e_tests import conftest

        template = MagicMock(status_code=200)
        template.json.return_value = {"properties": {"enable_backup": {}}}

        @asynccontextmanager
        async def get_template(*args):
            yield template

        for properties, expected in ((None, False), ({"enable_backup": True}, True)):
            post = AsyncMock(return_value=("/workspaces/w", "w"))
            with (
                self.subTest(properties=properties),
                patch.object(conftest, "get_admin_token", AsyncMock(return_value="token")),
                patch.object(conftest, "get_template", get_template),
                patch.object(conftest, "post_resource", post),
                patch.object(conftest.asyncio, "sleep", AsyncMock()),
                patch.object(conftest.config, "TEST_WORKSPACE_APP_PLAN", ""),
            ):
                await conftest.create_or_get_test_workspace("Automatic", True, properties=properties)
            self.assertIs(post.await_args.args[0]["properties"]["enable_backup"], expected)
