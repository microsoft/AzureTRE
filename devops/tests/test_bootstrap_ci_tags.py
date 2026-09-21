"""Check management ownership before a simulated early bootstrap failure."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "devops/terraform/bootstrap.sh"

MOCK_AZ = r'''
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["MOCK_ROOT"])
config = json.loads((root / "config.json").read_text())
args = sys.argv[1:]
with (root / "calls.jsonl").open("a") as log:
    log.write(json.dumps(args) + "\n")

if args[:2] == ["group", "exists"]:
    if config.get("exists_error"):
        sys.exit(37)
    print(config.get("exists_response", "true" if config.get("exists") else "false"))
elif args[:2] in (["group", "create"], ["group", "update"]):
    if config.get("write_error"):
        sys.exit(38)
    # Azure group create replaces tags, including clearing them when omitted.
    tags = {} if args[:2] == ["group", "create"] else (config.get("tags") or {}).copy()
    if "--tags" in args:
        key, value = args[args.index("--tags") + 1].split("=", 1)
        tags = {key: value}
    if "--set" in args:
        key, value = args[args.index("--set") + 1].split("=", 1)
        tags[key.removeprefix("tags.")] = value
    (root / "tags.json").write_text(json.dumps(tags))
elif args[:2] == ["storage", "account"]:
    # Stop before network access, identity lookup or Terraform. The ownership tag
    # must already exist even when storage account creation fails.
    print("Simulated storage account failure", file=sys.stderr)
    sys.exit(39)
else:
    sys.exit("Unexpected Azure command: " + " ".join(args))
'''


class BootstrapCiTagsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        mock = self.root / "az"
        mock.write_text(f"#!{sys.executable}\n" + MOCK_AZ)
        mock.chmod(0o755)
        self.env = {
            "PATH": str(self.root),
            "MOCK_ROOT": str(self.root),
            "TF_VAR_mgmt_resource_group_name": "rg-tretest-mgmt",
            "TF_VAR_mgmt_storage_account_name": "mockstorage",
            "LOCATION": "mock-location",
        }
        self.config = {}

    def run_bootstrap(self):
        (self.root / "config.json").write_text(json.dumps(self.config))
        result = subprocess.run(
            ["/bin/bash", str(BOOTSTRAP)], cwd=self.root, env=self.env,
            capture_output=True, text=True, timeout=10,
        )
        self.calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertNotIn("Unexpected Azure command", result.stderr)
        return result

    def tags(self):
        path = self.root / "tags.json"
        return json.loads(path.read_text()) if path.exists() else (self.config.get("tags") or {})

    def test_new_group_is_tagged_before_storage_creation_fails(self):
        self.env["TF_VAR_ci_git_ref"] = "refs/pull/5033/merge"
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertEqual(self.tags(), {"ci_git_ref": "refs/pull/5033/merge"})
        self.assertEqual([call[:2] for call in self.calls[:3]], [
            ["group", "exists"], ["group", "create"], ["storage", "account"],
        ])

    def test_existing_group_keeps_unrelated_tags(self):
        self.config = {"exists": True, "tags": {"project": "keep this", "owner": "platform"}}
        self.env["TF_VAR_ci_git_ref"] = "refs/heads/feature/test"
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertEqual(self.tags(), {
            "project": "keep this", "owner": "platform", "ci_git_ref": "refs/heads/feature/test",
        })
        self.assertEqual(self.calls[1][:2], ["group", "update"])
        self.assertFalse(any(call[:2] == ["group", "create"] for call in self.calls))

    def test_ci_reference_is_a_single_literal_argument(self):
        self.env["TF_VAR_ci_git_ref"] = 'refs/heads/feature/$(false);"quoted"'
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertEqual(self.tags()["ci_git_ref"], self.env["TF_VAR_ci_git_ref"])

    def test_non_ci_deployment_does_not_add_ownership_tag(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertEqual(self.tags(), {})
        self.assertEqual(self.calls[1][:2], ["group", "create"])
        self.assertNotIn("--tags", self.calls[1])

    def test_empty_ci_reference_does_not_overwrite_tags(self):
        self.env["TF_VAR_ci_git_ref"] = ""
        self.config = {"exists": True, "tags": {"owner": "platform", "ci_git_ref": "refs/heads/main"}}
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertFalse(any(call[:2] in (["group", "create"], ["group", "update"]) for call in self.calls))
        self.assertEqual(self.tags(), self.config["tags"])

    def test_unset_ci_reference_does_not_overwrite_tags(self):
        self.config = {"exists": True, "tags": {"owner": "platform", "ci_git_ref": "refs/heads/main"}}
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertFalse(any(call[:2] in (["group", "create"], ["group", "update"]) for call in self.calls))
        self.assertEqual(self.tags(), self.config["tags"])

    def test_existing_untagged_group_accepts_ci_reference(self):
        self.config = {"exists": True, "tags": None}
        self.env["TF_VAR_ci_git_ref"] = "refs/pull/5033/merge"
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 39, result.stderr)
        self.assertEqual(self.tags(), {"ci_git_ref": "refs/pull/5033/merge"})

    def test_non_ci_lookup_failure_stops_bootstrap(self):
        self.config["exists_error"] = True
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(len(self.calls), 1)

    def test_failed_new_group_creation_stops_bootstrap(self):
        self.env["TF_VAR_ci_git_ref"] = "refs/pull/5033/merge"
        self.config["write_error"] = True
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 38, result.stderr)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[-1][:2], ["group", "create"])

    def test_failed_group_lookup_does_not_attempt_creation(self):
        self.env["TF_VAR_ci_git_ref"] = "refs/pull/5033/merge"
        self.config["exists_error"] = True
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse((self.root / "tags.json").exists())

    def test_invalid_group_lookup_does_not_attempt_creation(self):
        self.env["TF_VAR_ci_git_ref"] = "refs/pull/5033/merge"
        self.config["exists_response"] = "unknown"
        result = self.run_bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("Could not determine", result.stderr)

    def test_failed_ownership_update_stops_bootstrap(self):
        self.env["TF_VAR_ci_git_ref"] = "refs/pull/5033/merge"
        self.config.update(exists=True, write_error=True)
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 38, result.stderr)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[-1][:2], ["group", "update"])

    def test_management_workflow_passes_ci_reference_as_environment_data(self):
        workflow = (ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text()
        management_step = workflow.split("- name: Deploy management\n", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn('COMMAND: "make bootstrap mgmt-deploy"', management_step)
        self.assertIn("CI_GIT_REF: ${{ inputs.ciGitRef }}", management_step)
        action = (ROOT / ".github/actions/devcontainer_run_command/action.yml").read_text()
        command_step = action.split("- name: Run command in DevContainer\n", 1)[1]
        self.assertIn("env:\n        TF_VAR_ci_git_ref: ${{ inputs.CI_GIT_REF }}", command_step)
        self.assertIn("-e TF_VAR_ci_git_ref \\\n", command_step)
        self.assertNotIn("${{ inputs.CI_GIT_REF }}", command_step.split("run: |", 1)[1])


if __name__ == "__main__":
    unittest.main()
