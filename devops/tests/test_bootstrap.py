"""Run bootstrap and management deployment with mocked external commands."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


DEVOPS = Path(__file__).resolve().parents[1]

# Azure CLI replaces storage error codes with these messages before printing them.
CLI_PERMISSION_ERROR = '''ERROR:
You do not have the required permissions needed to perform this operation.
Depending on your operation, you may need to be assigned one of the following roles:
    "Storage Blob Data Owner"
    "Storage Blob Data Contributor"
    "Storage Blob Data Reader"
    "Storage Queue Data Contributor"
    "Storage Queue Data Reader"
    "Storage Table Data Contributor"
    "Storage Table Data Reader"

If you want to use the old authentication method and allow querying for the right account key, please use the "--auth-mode" parameter and "key" value.
'''
CLI_NETWORK_ERROR = '''ERROR:
The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'.
If you want to change the default action to apply when no rule matches, please use 'az storage account update'.
'''

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
    "network_blob_checks": 0,
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
elif command == "update_tags.sh":
    finish()
elif command == "terraform":
    if args[0] == "init":
        check = "blob_checks" if config["script"] == "bootstrap.sh" else "network_blob_checks"
        if not state["public"] or state[check] == 0:
            finish(99, "Terraform started before checking blob access")
        index = state["init_calls"]
        state["init_calls"] += 1
        response("init_responses", index)
    elif args[:2] == ["state", "show"]:
        finish(1)
    elif args[0] == "import":
        finish()
    elif args[0] in ("plan", "apply"):
        response(f"{args[0]}_responses", 0)
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
            state["network_blob_checks"] += 1
            finish()
        if not state["role_created"] or "tfstate" not in state["containers"]:
            finish(99, "Blob readiness checked before role/container setup")
        index = state["blob_checks"]
        state["blob_checks"] += 1
        response("blob_responses", index)

finish(99, "Unexpected command: " + " ".join([command, *args]))
'''


class TerraformScriptTests(unittest.TestCase):
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
        for script in ("bootstrap.sh", "deploy.sh"):
            shutil.copy2(DEVOPS / "terraform" / script, self.terraform_dir)
        # Tag updates are outside these tests; record when deployment reaches them.
        (self.terraform_dir / "update_tags.sh").symlink_to(mock)
        for script in ("storage_enable_public_access.sh", "bash_trap_helper.sh", "terraform_init.sh"):
            shutil.copy2(DEVOPS / "scripts" / script, scripts)

    def run_script(self, script, **config):
        config["script"] = script
        (self.root / "config.json").write_text(json.dumps(config))
        result = subprocess.run(
            ["/bin/bash", script],
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


class BootstrapTests(TerraformScriptTests):
    def run_bootstrap(self, **config):
        return self.run_script("bootstrap.sh", **config)

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

    def test_cli_permission_messages_retry_until_blob_access_is_ready(self):
        result = self.run_bootstrap(blob_responses=[
            {"code": 1, "output": CLI_PERMISSION_ERROR},
            {"code": 1, "output": CLI_NETWORK_ERROR},
            {"code": 0, "output": ""},
        ])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.blob_checks()), 3)
        self.assertEqual(self.sleeps(), [10, 20])
        self.assertIn(CLI_PERMISSION_ERROR, self.output)
        self.assertIn(CLI_NETWORK_ERROR, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        init_index = self.calls.index(self.commands("terraform", "init")[0])
        self.assertEqual(self.calls[:init_index].count(self.blob_checks()[0]), 3)

    def test_cli_permission_message_retries_are_bounded(self):
        result = self.run_bootstrap(blob_responses=[{"code": 1, "output": CLI_PERMISSION_ERROR}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.blob_checks()), 6)
        self.assertEqual(self.sleeps(), [10, 20, 40, 80, 160])
        self.assertEqual(self.commands("terraform"), [])
        self.assertEqual(self.output.count(CLI_PERMISSION_ERROR), 6)
        self.assertIn("Terraform has not been started", self.output)

    def test_cli_network_message_retries_are_bounded(self):
        result = self.run_bootstrap(blob_responses=[{"code": 1, "output": CLI_NETWORK_ERROR}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.blob_checks()), 6)
        self.assertEqual(self.sleeps(), [10, 20, 40, 80, 160])
        self.assertEqual(self.commands("terraform"), [])
        self.assertEqual(self.output.count(CLI_NETWORK_ERROR), 6)
        self.assertIn("Terraform has not been started", self.output)

    def test_cli_authentication_failure_is_not_retried(self):
        error = "ERROR: Authentication failure. This may be caused by either invalid account key, connection string or sas token value provided for your storage account."
        result = self.run_bootstrap(blob_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.blob_checks()), 1)
        self.assertEqual(self.sleeps(), [])
        self.assertEqual(self.commands("terraform"), [])
        self.assertIn(error, self.output)

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

    def test_lock_error_takes_priority_over_cli_permission_message(self):
        result = self.run_bootstrap(init_responses=[{
            "code": 1,
            "output": f"Failed to get existing workspaces: {CLI_PERMISSION_ERROR}\nError unlocking Azure state. Lock ID: test-lock",
        }])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(CLI_PERMISSION_ERROR, self.output)
        self.assertIn("Check the reported lock owner", self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_imports()


class ManagementDeployTests(TerraformScriptTests):
    def run_deploy(self, **config):
        return self.run_script("deploy.sh", account_exists=True, containers=["tfstate", "tflogs"], **config)

    def assert_no_deployment(self):
        self.assertEqual(self.commands("terraform", "plan"), [])
        self.assertEqual(self.commands("terraform", "apply"), [])
        self.assertEqual(self.commands("update_tags.sh"), [])

    def assert_deployed_once(self):
        self.assertEqual(self.commands("terraform", "plan"), [["terraform", "plan", "-out", "devops.tfplan"]])
        self.assertEqual(self.commands("terraform", "apply"), [["terraform", "apply", "-auto-approve", "devops.tfplan"]])
        self.assertEqual(self.commands("update_tags.sh"), [["update_tags.sh"]])
        last_init = max(index for index, call in enumerate(self.calls) if call[:2] == ["terraform", "init"])
        plan = self.calls.index(self.commands("terraform", "plan")[0])
        apply = self.calls.index(self.commands("terraform", "apply")[0])
        tags = self.calls.index(self.commands("update_tags.sh")[0])
        self.assertLess(last_init, plan)
        self.assertLess(plan, apply)
        self.assertLess(apply, tags)

    def test_success_runs_plan_apply_and_tags_once_without_sleep(self):
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertIn("-no-color", self.commands("terraform", "init")[0])
        self.assertEqual(self.sleeps(), [])
        self.assert_deployed_once()

    def test_workspace_permission_failure_after_access_probe_is_retried(self):
        error = "Failed to get existing workspaces: listing blobs: executing request: unexpected status 403 (403 This request is not authorized to perform this operation.) with AuthorizationFailure: This request is not authorized to perform this operation."
        result = self.run_deploy(init_responses=[
            {"code": 1, "output": error},
            {"code": 0, "output": "Backend ready"},
        ])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertIn(error, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 2)
        self.assertEqual(self.sleeps(), [10])
        self.assert_deployed_once()

    def test_permission_timeout_stops_before_plan(self):
        error = "Failed to get existing workspaces: HTTP 403 AuthorizationFailure"
        result = self.run_deploy(init_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.commands("terraform", "init")), 6)
        self.assertEqual(self.sleeps(), [10, 20, 40, 80, 160])
        self.assertEqual(self.output.count(error), 6)
        self.assertIn("Terraform backend initialisation failed", self.output)
        self.assert_no_deployment()

    def test_final_init_attempt_can_succeed(self):
        result = self.run_deploy(init_responses=[
            *[{"code": 1, "output": "Failed to get existing workspaces: HTTP 403"}] * 5,
            {"code": 0, "output": "Backend ready"},
        ])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 6)
        self.assertEqual(self.sleeps(), [10, 20, 40, 80, 160])
        self.assert_deployed_once()

    def test_failed_unlock_takes_priority_over_workspace_permission_failure(self):
        error = "Failed to get existing workspaces: HTTP 403\nError unlocking Azure state. Lock ID: test-lock"
        result = self.run_deploy(init_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(error, self.output)
        self.assertIn("Check the reported lock owner", self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_deployment()

    def test_existing_lock_is_not_retried(self):
        error = "Error loading state: failed to lock azure state: state blob is already locked"
        result = self.run_deploy(init_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(error, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_deployment()

    def test_state_permission_error_is_not_retried(self):
        error = "Error loading state: HTTP 403"
        result = self.run_deploy(init_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(error, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_deployment()

    def test_unexpected_init_error_retains_diagnostics(self):
        result = self.run_deploy(init_responses=[{"code": 2, "output": "Invalid backend configuration"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("terraform init failed (exit 2)", self.output)
        self.assertIn("Invalid backend configuration", self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(self.sleeps(), [])
        self.assert_no_deployment()

    def test_plan_permission_failure_is_not_retried(self):
        error = "Failed to get existing workspaces: HTTP 403"
        result = self.run_deploy(plan_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(error, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(len(self.commands("terraform", "plan")), 1)
        self.assertEqual(self.commands("terraform", "apply"), [])
        self.assertEqual(self.commands("update_tags.sh"), [])
        self.assertEqual(self.sleeps(), [])

    def test_apply_permission_failure_is_not_retried(self):
        error = "Failed to get existing workspaces: HTTP 403"
        result = self.run_deploy(apply_responses=[{"code": 1, "output": error}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(error, self.output)
        self.assertEqual(len(self.commands("terraform", "init")), 1)
        self.assertEqual(len(self.commands("terraform", "plan")), 1)
        self.assertEqual(len(self.commands("terraform", "apply")), 1)
        self.assertEqual(self.commands("update_tags.sh"), [])
        self.assertEqual(self.sleeps(), [])


if __name__ == "__main__":
    unittest.main()
