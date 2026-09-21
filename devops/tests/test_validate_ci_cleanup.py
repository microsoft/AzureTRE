"""Exercise the live validation guard without Azure credentials or network access."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_ci_cleanup.py"
SPEC = importlib.util.spec_from_file_location("validate_ci_cleanup", SCRIPT)
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)

FAKE_COMMAND = r'''
import json
import os
from pathlib import Path
import re
import sys

path = Path(os.environ["FAKE_AZURE_STATE"])
state = json.loads(path.read_text())
args = sys.argv[1:]
command = Path(sys.argv[0]).name
if command == "gh":
    if any("/pulls?" in arg for arg in args):
        print("[]")
    else:
        print(json.dumps({"workflow_runs": state.get("workflows", [])}))
    sys.exit(0)
if command == "git":
    if args == ["show-ref"]:
        print("a" * 40 + " refs/remotes/origin/main")
        sys.exit(0)
    sys.exit(1)

with path.with_suffix(".calls").open("a") as log:
    log.write(json.dumps(args) + "\n")
assert args[-3:] == ["--subscription", "test-subscription", "--only-show-errors"]
args = args[:-3]

def option(*names):
    for name in names:
        if name in args:
            return args[args.index(name) + 1]
    return None

def values(name):
    result = []
    for value in args[args.index(name) + 1:]:
        if value.startswith("-"):
            break
        result.append(value)
    return result

group = option("--name", "--resource-group")
operation = args[:2]
groups = state["groups"]
result = None
if operation == ["account", "show"]:
    result = state["account"]
elif operation == ["group", "exists"]:
    result = group in groups
elif operation == ["group", "show"]:
    if group not in groups:
        sys.exit(3)
    result = groups[group]
elif operation == ["group", "create"]:
    tags = dict(value.split("=", 1) for value in values("--tags")) if "--tags" in args else {}
    groups[group] = {"name": group, "id": "/subscriptions/test-subscription/resourceGroups/" + group,
                     "tags": tags, "properties": {"provisioningState": "Succeeded"}}
    result = groups[group]
elif operation == ["group", "update"]:
    if "--remove" in args:
        sys.exit("az group update does not support --remove")
    if "--set" in args:
        for value in values("--set"):
            key, value = value.split("=", 1)
            assert key.startswith("tags.")
            groups[group]["tags"][key.removeprefix("tags.")] = value
    if "--tags" in args:
        groups[group]["tags"] = dict(value.split("=", 1) for value in values("--tags"))
    result = groups[group]
elif operation == ["group", "delete"]:
    del groups[group]
elif operation == ["group", "wait"]:
    assert group not in groups
elif operation == ["group", "list"]:
    result = list(groups.values())
    query = option("--query")
    if query:
        prefix = re.search(r"starts_with\(name, '([^']+)'\)", query).group(1)
        result = [row for row in result if row["name"].startswith(prefix)]
        if "ci_git_ref" in query:
            result = [{"name": row["name"], "ci_git_ref": row["tags"].get("ci_git_ref")} for row in result]
        else:
            print("\n".join(row["name"] for row in result))
            result = None
elif operation in (["resource", "list"], ["lock", "list"], ["acr", "list"], ["keyvault", "list"]):
    if option("--output", "-o") == "json":
        result = []
else:
    sys.exit("Unexpected Azure command reached the fake service")
path.write_text(json.dumps(state))
if result is not None:
    print(json.dumps(result))
'''


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runner = validation.Validation(self.root / "validation")
        self.runner.state = {
            "az": str(self.root / "az"), "subscription": "test-subscription", "tenant": "test-tenant",
            "identity": ["test-subscription", "test-tenant", "test-user", "user"], "owner": "123-1-test",
            "core": "rg-trevalidate-test", "groups": ["rg-trevalidate-test-mgmt", "rg-trevalidate-testother-mgmt"],
            "location": "westeurope", "ref": "refs/heads/ci-cleanup-validation/test", "main_id": "excluded",
            "commit": "a" * 40, "checks": [], "status": "running", "inventory": validation.inventory_digest([], []),
        }
        self.runner.save()
        self.target, self.neighbour = self.runner.state["groups"]
        self.metadata = {"id": "/subscriptions/test-subscription/resourceGroups/" + self.target,
                         "tags": {validation.OWNER_TAG: "123-1-test"}, "properties": {"provisioningState": "Succeeded"}}
        self.environment = patch.dict(os.environ, CLEANUP_VALIDATION_PHASE="apply", GITHUB_STEP_SUMMARY=str(self.root / "summary.md"))
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_guard_rejects_unrecognised_commands_before_azure(self):
        commands = [
            ["group", "delete", "--resource-group", self.neighbour, "--yes", "--no-wait"],
            ["group", "delete", "--resource-group", "rg-production", "--yes", "--no-wait"],
            ["group", "delete", "--resource-group", self.target, "--yes", "--no-wait", "--subscription", "other"],
            ["resource", "delete", "--ids", "/subscriptions/other"],
            ["group", "show", "--name", self.runner.state["core"]],
            ["account", "get-access-token"], ["group", "list"],
        ]
        with patch.object(self.runner, "azure") as azure:
            for args in commands:
                with self.subTest(args=args), self.assertRaises(validation.ValidationError):
                    self.runner.guard(args)
            azure.assert_not_called()

    def test_delete_requires_unchanged_ci_reference(self):
        with patch.object(self.runner, "owned_empty", return_value=self.metadata), patch.object(self.runner, "azure") as azure:
            with self.assertRaisesRegex(validation.ValidationError, "ownership reference"):
                self.runner.guard(["group", "delete", "--resource-group", self.target, "--yes", "--no-wait"])
            azure.assert_not_called()

    def test_azure_failure_reports_operation_without_private_arguments_or_output(self):
        result = subprocess.CompletedProcess([], 2, "private stdout", "private stderr")
        with patch.object(validation.subprocess, "run", return_value=result):
            with self.assertRaises(validation.ValidationError) as raised:
                self.runner.azure(["group", "update", "--name", "private-group"])
        self.assertEqual(str(raised.exception), "Azure CLI group update failed (exit 2). Raw Azure output is withheld.")

    def test_empty_group_checks_reject_mismatched_identity_tags_contents_and_locks(self):
        cases = [
            ({**self.metadata, "id": "/subscriptions/other/resourceGroups/" + self.target}, [], []),
            ({**self.metadata, "tags": {}}, [], []),
            ({**self.metadata, "properties": {"provisioningState": "Updating"}}, [], []),
            (self.metadata, [{"name": "storage"}], []),
            (self.metadata, [], [{"name": "lock"}]),
        ]
        for metadata, resources, locks in cases:
            with self.subTest(metadata=metadata, resources=resources, locks=locks):
                with patch.object(self.runner, "identity"), patch.object(self.runner, "azure_json", side_effect=[metadata, resources, locks]):
                    with self.assertRaises(validation.ValidationError):
                        self.runner.owned_empty(self.target)
        account = {"id": "other", "tenantId": "test-tenant", "user": {"name": "test-user", "type": "user"}}
        with patch.object(self.runner, "azure_json", return_value=account), self.assertRaises(validation.ValidationError):
            self.runner.owned_empty(self.target)

    def test_cleanup_skip_and_missing_delete_do_not_pass(self):
        for output, error in [("Skipping environment cleanup while other workflow runs are queued:", validation.Incomplete),
                              ("", validation.ValidationError)]:
            with self.subTest(output=output), patch.object(self.runner, "script", return_value=subprocess.CompletedProcess([], 0, output, "")):
                with self.assertRaises(error):
                    self.runner.cleanup_script(preview=True)

    def test_cleanup_attempts_both_groups_after_one_fails(self):
        with patch.object(self.runner, "azure_json", side_effect=[True, True, []]), \
                patch.object(self.runner, "owned_group", side_effect=validation.ValidationError("Ownership changed")) as owned:
            with self.assertRaises(validation.ValidationError):
                self.runner.cleanup_fixtures()
            self.assertEqual([call.args[0] for call in owned.call_args_list], [self.target, self.neighbour])
            self.assertFalse(self.runner.state["fixtures_deleted"])

    def test_cleanup_waits_for_owned_group_already_deleting(self):
        metadata = {**self.metadata, "properties": {"provisioningState": "Deleting"}}
        with patch.object(self.runner, "azure_json", side_effect=[True, False, []]), \
                patch.object(self.runner, "owned_group", return_value=metadata), patch.object(self.runner, "azure") as azure, \
                patch.object(self.runner, "wait_deleted") as wait:
            self.runner.cleanup_fixtures()
            wait.assert_called_once_with(self.target)
            azure.assert_not_called()
            self.assertTrue(self.runner.state["fixtures_deleted"])

    def test_inventory_detects_non_fixture_changes(self):
        rows = [{"name": "rg-existing", "tags": {"keep": "yes"}}, {"name": self.target, "tags": {}}]
        before = validation.inventory_digest(rows, [self.target])
        rows[-1]["tags"]["changed"] = "yes"
        self.assertEqual(before, validation.inventory_digest(rows, [self.target]))
        rows[0]["tags"]["keep"] = "no"
        self.assertNotEqual(before, validation.inventory_digest(rows, [self.target]))

    def test_summary_requires_validation_cleanup_and_inventory_success(self):
        cases = [("passed", True, True, 0), ("passed", False, True, 1), ("passed", True, False, 1),
                 ("incomplete", True, True, 1), ("failed", True, True, 1), ("running", True, True, 1)]
        for status, deleted, unchanged, expected in cases:
            with self.subTest(status=status, deleted=deleted, unchanged=unchanged):
                self.runner.state.update(status=status, fixtures_deleted=deleted, inventory_unchanged=unchanged)
                self.assertEqual(self.runner.summary(), expected)
                evidence = (self.runner.root / "evidence/results.json").read_text()
                self.assertEqual(json.loads(evidence)["status"] == "passed", expected == 0)
                for private in ("test-subscription", "test-tenant", "test-user", str(self.root)):
                    self.assertNotIn(private, evidence)

    def fake_services(self):
        path = self.root / "azure.json"
        account = {"id": "test-subscription", "tenantId": "test-tenant", "user": {"name": "test-user", "type": "user"}}
        path.write_text(json.dumps({"groups": {}, "account": account}))
        for command in ("az", "gh", "git"):
            script = self.root / command
            script.write_text(f"#!{sys.executable}\n" + FAKE_COMMAND)
            script.chmod(0o755)
        env = patch.dict(os.environ, FAKE_AZURE_STATE=str(path), PATH=str(self.root) + os.pathsep + os.environ["PATH"],
                         GITHUB_REPOSITORY="example/test", GITHUB_RUN_ID="123")
        env.start()
        self.addCleanup(env.stop)
        return path

    def test_real_scripts_complete_guarded_lifecycle_without_creating_storage(self):
        path = self.fake_services()
        self.runner.scenarios()
        self.assertEqual(len(self.runner.state["checks"]), 9)
        self.assertEqual(json.loads(path.read_text())["groups"][self.neighbour]["tags"],
                         {validation.OWNER_TAG: self.runner.state["owner"], "validation_keep": "preserved"})
        self.runner.cleanup_script(preview=True)
        self.assertEqual(len(json.loads(path.read_text())["groups"]), 2)
        self.runner.cleanup_script(preview=False)
        self.assertEqual(list(json.loads(path.read_text())["groups"]), [self.neighbour])
        self.runner.state["status"] = "passed"
        self.runner.cleanup_fixtures()
        self.assertEqual(json.loads(path.read_text())["groups"], {})
        self.assertEqual(self.runner.summary(), 0)
        calls = [json.loads(line) for line in path.with_suffix(".calls").read_text().splitlines()]
        self.assertFalse(any(call[0] == "storage" for call in calls))

    def test_partial_bootstrap_failure_still_removes_fixtures(self):
        path = self.fake_services()
        self.runner.bootstrap("Created fixture", self.target, self.runner.state["ref"], {"ci_git_ref": self.runner.state["ref"]})
        self.runner.state["status"] = "failed"
        self.runner.cleanup_fixtures()
        self.assertEqual(json.loads(path.read_text())["groups"], {})
        self.assertEqual(self.runner.summary(), 1)


if __name__ == "__main__":
    unittest.main()
