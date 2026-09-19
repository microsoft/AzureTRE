"""Run bootstrap with mocked Azure, Terraform and sleep commands."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


DEVOPS = Path(__file__).resolve().parents[1]

MOCK_COMMAND = r'''
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["MOCK_ROOT"])
config = json.loads((root / "config.json").read_text())
state_path = root / "state.json"
state = json.loads(state_path.read_text()) if state_path.exists() else {
    "account_exists": config.get("account_exists", False),
    "public": False,
    "containers": config.get("containers", []),
    "role_created": False,
    "blob_checks": 0,
    "init_calls": 0,
}
command = Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "calls.jsonl").open("a") as log:
    log.write(json.dumps([command, *args]) + "\n")


def finish(code=0, output=""):
    state_path.write_text(json.dumps(state))
    if output:
        print(output, file=sys.stderr if code else sys.stdout)
    sys.exit(code)


def response(name, index):
    responses = config.get(name, [{"code": 0, "output": ""}])
    item = responses[min(index, len(responses) - 1)]
    finish(item["code"], item["output"])


if command == "sleep":
    finish()
elif command == "terraform":
    if args[0] == "init":
        if state["blob_checks"] == 0:
            finish(99, "Terraform started before checking blob access")
        index = state["init_calls"]
        state["init_calls"] += 1
        response("init_responses", index)
    elif args[:2] == ["state", "show"]:
        finish(1)
    elif args[0] == "import":
        finish()
elif command == "az":
    if args[:2] == ["group", "create"]:
        finish()
    elif args[:3] == ["storage", "account", "show"]:
        finish(0 if state["account_exists"] else 1, "mock-account" if state["account_exists"] else "")
    elif args[:3] == ["storage", "account", "create"]:
        state["account_exists"] = True
        finish()
    elif args[:3] == ["storage", "account", "update"]:
        state["public"] = args[args.index("--public-network-access") + 1] == "Enabled"
        finish()
    elif args[:3] in (["ad", "sp", "show"], ["ad", "signed-in-user", "show"]):
        finish(output="mock-principal")
    elif args[:3] == ["role", "assignment", "create"]:
        state["role_created"] = True
        finish()
    elif args[:3] == ["role", "assignment", "list"]:
        finish(output="Storage Blob Data Contributor")
    elif args[:3] == ["storage", "container", "list"]:
        if not state["public"]:
            finish(1, "AuthorizationFailure")
        finish(output="\n".join(state["containers"]))
    elif args[:3] == ["storage", "container", "create"]:
        container = args[args.index("--name") + 1]
        if container not in state["containers"]:
            state["containers"].append(container)
        finish()
    elif args[:3] == ["storage", "blob", "list"]:
        if not state["public"]:
            finish(1, "AuthorizationFailure")
        if "--prefix" not in args:
            # Existing containers may be checked by the network-access helper.
            finish()
        if not state["role_created"] or "tfstate" not in state["containers"]:
            finish(99, "Blob readiness checked before role/container setup")
        index = state["blob_checks"]
        state["blob_checks"] += 1
        response("blob_responses", index)

finish(99, "Unexpected command: " + " ".join([command, *args]))
'''


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        mock = self.root / "mock.py"
        mock.write_text(f"#!{sys.executable}\n" + MOCK_COMMAND)
        mock.chmod(0o755)
        for command in ("az", "terraform", "sleep"):
            (self.bin_dir / command).symlink_to(mock)
        self.terraform_dir = self.root / "devops" / "terraform"
        self.terraform_dir.mkdir(parents=True)
        scripts = self.root / "devops" / "scripts"
        scripts.mkdir()
        shutil.copy2(DEVOPS / "terraform" / "bootstrap.sh", self.terraform_dir)
        for script in ("storage_enable_public_access.sh", "bash_trap_helper.sh"):
            shutil.copy2(DEVOPS / "scripts" / script, scripts)

    def run_bootstrap(self, **config):
        (self.root / "config.json").write_text(json.dumps(config))
        result = subprocess.run(
            ["/bin/bash", "bootstrap.sh"],
            cwd=self.terraform_dir,
            env={
                "PATH": f"{self.bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
                "MOCK_ROOT": str(self.root),
                "PYTHONDONTWRITEBYTECODE": "1",
                "ARM_CLIENT_ID": "mock-client",
                "ARM_SUBSCRIPTION_ID": "mock-subscription",
                "TF_VAR_mgmt_resource_group_name": "mock-rg",
                "TF_VAR_mgmt_storage_account_name": "mockstorage",
                "TF_VAR_terraform_state_container_name": "tfstate",
                "LOCATION": "mock-location",
            },
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.output = result.stdout + result.stderr
        self.assertNotIn("Unexpected command:", self.output)
        self.assertNotIn("before role/container setup", self.output)
        self.assertNotIn("before checking blob access", self.output)
        # The real EXIT trap must close network access on both success and failure.
        updates = self.commands("az", "storage", "account", "update")
        self.assertEqual(len(updates), 2, self.output)
        self.assertIn("Disabled", updates[-1])
        self.assertIn("Deny", updates[-1])
        self.assertEqual(self.commands("az", "storage", "blob", "lease"), [])
        self.assertEqual(self.commands("terraform", "force-unlock"), [])
        return result

    def commands(self, *prefix):
        return [call for call in self.calls if call[:len(prefix)] == list(prefix)]

    def blob_checks(self):
        return [call for call in self.commands("az", "storage", "blob", "list") if "--prefix" in call]

    def sleeps(self):
        return [int(call[1]) for call in self.commands("sleep")]

    def assert_no_imports(self):
        self.assertEqual(self.commands("terraform", "import"), [])

    def test_new_empty_account_checks_blob_data_before_init(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.blob_checks()), 1)
        check = self.blob_checks()[0]
        self.assertEqual(check[check.index("--auth-mode") + 1], "login")
        self.assertEqual(check[check.index("--container-name") + 1], "tfstate")
        self.assertEqual(check[check.index("--num-results") + 1], "1")
        self.assertEqual(check[check.index("--output") + 1], "none")
        init = self.commands("terraform", "init")[0]
        self.assertLess(self.calls.index(check), self.calls.index(init))
        self.assertIn("-no-color", init)
        self.assertEqual(len(self.commands("terraform", "import")), 2)
        self.assertEqual(self.sleeps(), [])

    def test_existing_account_still_checks_blob_data_before_init(self):
        result = self.run_bootstrap(account_exists=True, containers=["tfstate", "tflogs"])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.commands("az", "storage", "account", "create"), [])
        self.assertEqual(len(self.blob_checks()), 1)

    def test_role_presence_and_container_creation_do_not_skip_permission_wait(self):
        result = self.run_bootstrap(blob_responses=[
            {"code": 1, "output": "AuthorizationPermissionMismatch: initial denial"},
            {"code": 1, "output": "AuthorizationFailure: access is not ready"},
            {"code": 0, "output": ""},
        ])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.blob_checks()), 3)
        self.assertEqual(self.sleeps(), [10, 20])
        self.assertIn("initial denial", self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)

    def test_permission_timeout_never_starts_terraform(self):
        result = self.run_bootstrap(blob_responses=[{"code": 1, "output": "HTTP 403 Forbidden"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.blob_checks()), 6)
        self.assertEqual(self.sleeps(), [10, 20, 40, 80, 160])
        self.assertEqual(self.commands("terraform"), [])
        self.assertIn("Terraform has not been started", self.output)

    def test_final_wait_is_followed_by_one_last_check(self):
        result = self.run_bootstrap(blob_responses=[
            *[{"code": 1, "output": "HTTP 403"}] * 5,
            {"code": 0, "output": ""},
        ])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.blob_checks()), 6)
        self.assertEqual(self.sleeps(), [10, 20, 40, 80, 160])

    def test_unexpected_blob_error_is_not_retried(self):
        result = self.run_bootstrap(blob_responses=[{"code": 1, "output": "ContainerNotFound"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.blob_checks()), 1)
        self.assertEqual(self.sleeps(), [])
        self.assertEqual(self.commands("terraform"), [])
        self.assertIn("ContainerNotFound", self.output)

    def test_403_inside_identifier_is_not_a_permission_error(self):
        result = self.run_bootstrap(blob_responses=[{"code": 1, "output": "ContainerNotFound RequestId=abc403def"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.blob_checks()), 1)
        self.assertEqual(self.sleeps(), [])

    def test_terraform_success_uses_exit_status_not_output_phrase(self):
        result = self.run_bootstrap(init_responses=[{"code": 0, "output": "Backend ready"}])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertIn("Backend ready", self.output)

    def test_success_phrase_does_not_override_failed_exit_status(self):
        result = self.run_bootstrap(init_responses=[{"code": 1, "output": "Terraform has been successfully initialized\nLater failure"}])
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_imports()
        self.assertEqual(self.sleeps(), [])
        self.assertIn("terraform init failed (exit 1)", self.output)

    def test_pre_lock_workspace_permission_error_can_retry(self):
        result = self.run_bootstrap(init_responses=[
            {"code": 1, "output": "Failed to get existing workspaces: HTTP 403"},
            {"code": 0, "output": "Backend ready"},
        ])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 2)
        self.assertEqual(self.sleeps(), [10])
        self.assertIn("Failed to get existing workspaces: HTTP 403", self.output)

    def test_workspace_error_without_permission_failure_is_not_retried(self):
        result = self.run_bootstrap(init_responses=[{"code": 1, "output": "Failed to get existing workspaces: HTTP 404"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_imports()

    def test_workspace_permission_retries_are_bounded(self):
        error = "Failed to get existing workspaces: AuthorizationPermissionMismatch"
        result = self.run_bootstrap(init_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.commands("terraform", "init")), 6)
        self.assertEqual(self.sleeps(), [10, 20, 40, 80, 160])
        self.assertEqual(self.output.count(error), 6)
        self.assertIn("Terraform backend initialisation failed", self.output)
        self.assert_no_imports()

    def test_unknown_init_permission_error_is_not_blindly_retried(self):
        result = self.run_bootstrap(init_responses=[{"code": 1, "output": "Error loading state: HTTP 403"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assertIn("Error loading state: HTTP 403", self.output)
        self.assert_no_imports()

    def test_failed_unlock_with_403_is_visible_and_not_retried(self):
        error = "Error unlocking Azure state. Lock ID: test-lock\nError: failed to delete lock info from metadata: HTTP 403"
        result = self.run_bootstrap(init_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(error, self.output)
        self.assertIn("Check the reported lock owner", self.output)
        self.assertNotIn("Timeout waiting for Terraform backend role assignments", self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_imports()

    def test_existing_lock_is_not_retried_or_released(self):
        error = "Error loading state: failed to lock azure state: state blob is already locked"
        result = self.run_bootstrap(init_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(error, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_imports()

    def test_lock_error_takes_priority_over_workspace_permission_error(self):
        result = self.run_bootstrap(init_responses=[{
            "code": 1,
            "output": "Failed to get existing workspaces: HTTP 403\nError unlocking Azure state. Lock ID: test-lock",
        }])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_imports()

    def test_non_permission_terraform_error_retains_diagnostics(self):
        result = self.run_bootstrap(init_responses=[{"code": 2, "output": "Invalid backend configuration"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("terraform init failed (exit 2)", self.output)
        self.assertIn("Invalid backend configuration", self.output)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_imports()


if __name__ == "__main__":
    unittest.main()
