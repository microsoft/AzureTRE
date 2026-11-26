"""Check the file share backup probe, the Azure Backup helpers and the backup case set-up."""

from contextlib import asynccontextmanager
import json
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from jsonschema import validate
import yaml

from api_app.services.schema_service import enrich_user_resource_template
from e2e_tests import test_backup_restore as case
from e2e_tests.resources import backup
from e2e_tests.resources import backup_probe as probe
from e2e_tests.resources import sql_lifecycle

ROOT = Path(__file__).resolve().parents[2]
VAULT = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd/providers/Microsoft.RecoveryServices/vaults/arsv-tre-ws-abcd"
ACCOUNT = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd/providers/Microsoft.Storage/storageAccounts/stgwsabcd"
ITEM = f"{VAULT}/backupFabrics/Azure/protectionContainers/StorageContainer;storage;rg;stgwsabcd/protectedItems/AzureFileShare;x"
PROBE_ID = "0123456789abcdef0123456789abcdef"
WORKSPACE = "00000000-0000-0000-0000-00000000abcd"
# The names of the group, the vault and the account have only the last four characters of the workspace ID.
OTHER_WORKSPACE = "11111111-1111-1111-1111-11111111abcd"


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
    def test_the_custom_job_gives_the_lifecycle_cases_one_deadline_from_the_job_start(self):
        # One selection can run more than one lifecycle case in the same 300-minute job.
        jobs = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())["jobs"]
        steps = jobs["e2e_tests_custom"]["steps"]
        reserve = next(s for s in steps if "LIFECYCLE_VALIDATION_DEADLINE" in s.get("run", ""))
        run = next(s for s in steps if s["name"] == "Run E2E Tests")
        self.assertEqual(steps.index(reserve), 0)
        self.assertIn("270 * 60", reserve["run"])
        for variable in (
            "BACKUP_VALIDATION_DEADLINE",
            "AIRLOCK_MIGRATION_VALIDATION_DEADLINE",
            "AIRLOCK_UPGRADE_VALIDATION_DEADLINE",
            "PORTER_UPGRADE_VALIDATION_DEADLINE",
            "SQL_VALIDATION_DEADLINE",
            "MYSQL_VALIDATION_DEADLINE",
            "GITEA_VALIDATION_DEADLINE",
            "HEALTH_VALIDATION_DEADLINE",
            "CYCLECLOUD_VALIDATION_DEADLINE",
            "OHDSI_VALIDATION_DEADLINE",
        ):
            self.assertIn(f"{variable}=${{{{ env.LIFECYCLE_VALIDATION_DEADLINE }}}}", run["with"]["COMMAND"])

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
        self.text = ""

    def json(self):
        return self._body


def fake_arm(post=None, get=None, request=None, send=None):
    credential = SimpleNamespace(get_token=lambda scope: SimpleNamespace(token="token"))
    client = SimpleNamespace(
        post=AsyncMock(return_value=post), get=AsyncMock(side_effect=get or []), request=AsyncMock(side_effect=send)
    )
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

    def retained_backup_requests(self, group, soft_delete, refused=(), owners=None, statuses=None):
        """Give the calls and the ARM client of a removal.

        owners gives the tre_workspace_id tag of a resource, or None for no tag.
        Azure refuses a change to a resource in refused, and the soft delete change with soft delete on, with HTTP 400.
        statuses gives the HTTP statuses of the first changes to a resource.
        """
        calls = []
        owners = owners or {}
        statuses = {resource: list(codes) for resource, codes in (statuses or {}).items()}

        async def send(method, url, **kwargs):
            # The removal sends these changes through the HTTP client, because it reads their status.
            resource_id = url.removeprefix(backup.ARM)
            calls.append((method, resource_id))
            if statuses.get(resource_id):
                return FakeResponse(statuses[resource_id].pop(0))
            refusal = resource_id in refused or (resource_id.endswith("/vaultconfig") and soft_delete == "Enabled")
            return FakeResponse(400 if refusal else 202)

        async def request(method, resource_id, api_version, **kwargs):
            calls.append((method, resource_id))
            if method != "GET":
                return {}
            if resource_id.endswith("/vaultconfig"):
                return {"properties": {"softDeleteFeatureState": soft_delete}}
            if resource_id.endswith("/locks"):
                return {"value": [{"id": f"{group}/providers/Microsoft.Authorization/locks/backup"}]}
            if resource_id.endswith("/backupProtectedItems"):
                return {"value": [{"id": "/Subscriptions/" + ITEM.removeprefix("/subscriptions/"), "properties": {}}]}
            # The group, the vault and the account exist before their delete. Each wait sees the resource gone.
            if resource_id in {resource for verb, resource in calls if verb == "DELETE"}:
                return None
            owner = owners.get(resource_id, WORKSPACE)
            return {"tags": {"tre_workspace_id": owner}} if owner else {}

        return calls, fake_arm(request=request, send=send)

    async def test_the_retained_vault_is_removed_with_soft_delete_off_first(self):
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        calls, arm = self.retained_backup_requests(group, "Disabled")

        await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
        deletes = [resource for method, resource in calls if method == "DELETE"]
        # The removal reads the group, the vault and the account before its first change.
        soft_delete_off = ("PATCH", f"{VAULT}/backupconfig/vaultconfig")
        self.assertEqual(calls[:4], [("GET", group), ("GET", VAULT), ("GET", ACCOUNT), soft_delete_off])
        change = arm.client.request.await_args
        self.assertEqual(change.args, ("PATCH", f"{backup.ARM}{VAULT}/backupconfig/vaultconfig"))
        self.assertEqual(change.kwargs["params"], {"api-version": backup.BACKUP_API})
        self.assertEqual(change.kwargs["json"], {"properties": {"softDeleteFeatureState": "Disabled"}})
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

    async def test_a_vault_with_soft_delete_is_removed_when_azure_allows_it(self):
        # The workspace delete removed such a vault after it unregistered the container.
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        calls, arm = self.retained_backup_requests(group, "Enabled")

        await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
        deletes = [resource for method, resource in calls if method == "DELETE"]
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

    async def test_a_vault_that_keeps_soft_delete_stays_with_a_delete_date(self):
        # Azure keeps deleted backup data for 14 days and can refuse the delete of a vault with that data.
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        container = ITEM.split("/protectedItems/")[0]
        calls, arm = self.retained_backup_requests(group, "Enabled", refused=(container, VAULT))

        await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
        deletes = [resource for method, resource in calls if method == "DELETE"]
        self.assertEqual(
            deletes, [ITEM, container, VAULT, f"{group}/providers/Microsoft.Authorization/locks/backup", ACCOUNT]
        )
        self.assertEqual(calls[-1], ("PATCH", f"{group}/providers/Microsoft.Resources/tags/default"))
        tags = arm.request.await_args.kwargs["body"]["properties"]["tags"]
        self.assertRegex(tags["e2e_delete_after"], r"^\d{4}-\d{2}-\d{2}$")

    def assert_the_kept_vault_steps_did_not_run(self, calls, group):
        self.assertNotIn(("DELETE", ACCOUNT), calls)
        self.assertNotIn(("PATCH", f"{group}/providers/Microsoft.Resources/tags/default"), calls)

    async def test_an_error_that_is_not_a_refusal_fails_the_removal(self):
        # Only HTTP 400 shows that Azure refuses a change. Another error must not look like a kept vault.
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        container = ITEM.split("/protectedItems/")[0]
        for resource in (f"{VAULT}/backupconfig/vaultconfig", container, VAULT):
            for status in (401, 403, 409, 429, 500):
                with self.subTest(resource=resource, status=status):
                    calls, arm = self.retained_backup_requests(
                        group,
                        "Enabled",
                        refused=(container, VAULT),
                        statuses={resource: [status] * backup.CHANGE_ATTEMPTS},
                    )
                    with self.assertRaisesRegex(RuntimeError, f"HTTP {status}"):
                        await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
                    self.assert_the_kept_vault_steps_did_not_run(calls, group)

    async def test_a_change_gets_new_attempts_after_throttling_or_a_server_error(self):
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        calls, arm = self.retained_backup_requests(group, "Enabled", statuses={VAULT: [429, 503]})

        await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
        self.assertEqual(calls.count(("DELETE", VAULT)), 3)
        self.assertIn(("DELETE", group), calls)
        self.assert_the_kept_vault_steps_did_not_run(calls, group)

    async def test_a_vault_delete_that_does_not_end_fails_the_removal(self):
        # Azure accepted the delete, so a vault that stays is not a refusal.
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        calls, arm = self.retained_backup_requests(group, "Enabled")

        async def wait(arm, resource_id, api_version, minutes):
            if resource_id == VAULT:
                raise TimeoutError

        with patch.object(backup, "wait_until_gone", wait), self.assertRaises(TimeoutError):
            await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
        self.assert_the_kept_vault_steps_did_not_run(calls, group)

    async def test_nothing_is_removed_when_the_resource_group_is_gone(self):
        arm = fake_arm(request=[None])
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
        self.assertEqual(arm.request.await_count, 1)

    async def test_a_resource_of_another_workspace_stops_the_removal_before_the_first_change(self):
        # A failed install can leave these names with the group of another workspace. Terraform gives the tag
        # to each resource that it creates, so a resource without the tag is not from the workspace of the case.
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        for resource in (group, VAULT, ACCOUNT):
            for owner in (OTHER_WORKSPACE, None):
                with self.subTest(resource=resource, owner=owner):
                    calls, arm = self.retained_backup_requests(group, "Disabled", owners={resource: owner})
                    with self.assertRaisesRegex(AssertionError, "tre_workspace_id"):
                        await backup.remove_retained_backup(arm, WORKSPACE, group, VAULT, ACCOUNT)
                    self.assertEqual({method for method, _ in calls}, {"GET"})


class KeptBackupCleanupTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def workspace_status(self, code):
        """Give the status of the workspace read to the clean-up, and yield the mock of the backup removal."""
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=SimpleNamespace(get=AsyncMock(return_value=FakeResponse(code))))
        client.__aexit__ = AsyncMock(return_value=False)
        arm = MagicMock()
        arm.__aenter__ = AsyncMock(return_value="arm")
        arm.__aexit__ = AsyncMock(return_value=False)
        with (
            patch.object(case, "AsyncClient", return_value=client),
            patch.object(case, "get_admin_token", AsyncMock(return_value="token")),
            patch.object(case, "arm_client", return_value=arm),
            patch.object(case, "remove_retained_backup", AsyncMock()) as remove,
        ):
            yield remove

    async def test_the_kept_backup_is_removed_only_after_the_api_deleted_the_workspace(self):
        for code, removed in ((404, True), (200, False)):
            with self.subTest(code=code):
                async with self.workspace_status(code) as remove:
                    await case.remove_kept_backup("/workspaces/w", WORKSPACE, "/group", VAULT, ACCOUNT, True)
                if removed:
                    remove.assert_awaited_once_with("arm", WORKSPACE, "/group", VAULT, ACCOUNT)
                else:
                    remove.assert_not_awaited()

    async def test_a_failed_workspace_read_fails_the_cleanup_of_the_kept_backup(self):
        # Only HTTP 200 shows that the workspace exists. Another status must not hide a kept backup.
        for code in (401, 403, 429, 500, 503):
            with self.subTest(code=code):
                async with self.workspace_status(code) as remove:
                    with self.assertRaisesRegex(AssertionError, f"Actual: {code}"):
                        await case.remove_kept_backup("/workspaces/w", WORKSPACE, "/group", VAULT, ACCOUNT, True)
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

    async def test_a_failed_early_delete_is_not_sent_again(self):
        # A failed delete stays for diagnosis, so the reserved clean-up does not send it again.
        resources = sql_lifecycle.SQLResources(False, sql_lifecycle.asyncio.get_running_loop().time() + 60)
        failed = AsyncMock(side_effect=AssertionError("deleting_failed"))
        resources.own("/one", failed)
        with self.assertRaises(AssertionError):
            await resources.delete_now("/one")
        self.assertEqual(await resources.close(), [])
        failed.assert_awaited_once()

    async def run_case_with_a_failed_setup(self, create, error, token_error=None):
        """Run the retain case until its set-up fails with the error, and return the clean-ups that it owns then."""
        resources = sql_lifecycle.SQLResources(False, 0)

        @asynccontextmanager
        async def lifecycle(verify, deadline_variable):
            yield resources

        with (
            patch.dict(case.os.environ, {"AZURE_ENVIRONMENT": "AzureCloud", "ARM_SUBSCRIPTION_ID": "sub"}),
            patch.object(case.config, "TRE_ID", "tre"),
            patch.object(case, "sql_lifecycle", lifecycle),
            patch.object(sql_lifecycle, "create_or_get_test_workspace", create),
            patch.object(sql_lifecycle, "get_workspace_owner_token", AsyncMock(side_effect=token_error)),
        ):
            with self.assertRaisesRegex(type(error), str(error)):
                await case.test_file_share_restore_and_workspace_delete(False, False)
        return resources.finalisers

    async def test_the_kept_backup_is_owned_before_a_failed_workspace_install(self):
        # The clean-up of a failed install deletes the workspace, and that delete keeps the backup resources.
        failed_install = AssertionError("deployment_failed")

        async def create(**kwargs):
            kwargs["accepted"]("/workspaces/w", "w-abcd")
            raise failed_install

        finalisers = await self.run_case_with_a_failed_setup(create, failed_install)
        self.assertEqual([name for name, _ in finalisers], ["retained backup"])
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        self.assertEqual(finalisers[0][1].args[:5], ("/workspaces/w", "w-abcd", group, VAULT, ACCOUNT))

    async def test_the_kept_backup_is_owned_before_the_owner_token_lookup(self):
        # A failed lookup after the workspace install must not leave the kept backup without its clean-up.
        async def create(**kwargs):
            kwargs["accepted"]("/workspaces/w", "w-abcd")
            return "/workspaces/w", "w-abcd"

        no_token = RuntimeError("no token")
        finalisers = await self.run_case_with_a_failed_setup(create, no_token, token_error=no_token)
        self.assertEqual([name for name, _ in finalisers], ["retained backup", "/workspaces/w"])
        group = "/subscriptions/sub/resourceGroups/rg-tre-ws-abcd"
        self.assertEqual(finalisers[0][1].args[:3], ("/workspaces/w", "w-abcd", group))

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
