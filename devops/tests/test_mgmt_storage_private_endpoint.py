"""Exercise the core management storage private endpoint step with mocked tools."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "core/terraform/mgmt_storage_private_endpoint.sh"
PE_ADDRESS = "module.resource_processor_vmss_porter[0].azurerm_private_endpoint.mgmtblobpe"
HOST = "mockstorage.blob.core.windows.net"

MOCK_COMMAND = r"""
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["MOCK_ROOT"])
config = json.loads((root / "config.json").read_text())
state_file = root / "state.json"
state = json.loads(state_file.read_text()) if state_file.exists() else {"lookups": 0}
args = sys.argv[1:]
command = Path(sys.argv[0]).name
with (root / "calls.jsonl").open("a") as log:
    log.write(json.dumps([command, *args]) + "\n")


def finish(code=0, output=""):
    state_file.write_text(json.dumps(state))
    if output:
        print(output, file=sys.stderr if code else sys.stdout)
    sys.exit(code)


if command == "sleep":
    finish()
if command == "az" and args[:3] == ["storage", "account", "show"]:
    finish(output="https://mockstorage.blob.core.windows.net/")
if command == "terraform" and args[:2] == ["state", "list"]:
    finish(output="\n".join(config["state"]))
if command == "terraform" and args[0] == "plan":
    finish()
if command == "terraform" and args[0] == "apply":
    finish(config["apply_exit"], "apply failed" if config["apply_exit"] else "")
if command == "getent":
    calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
    if not any(call[:2] == ["terraform", "apply"] for call in calls):
        finish(output="20.0.0.1 STREAM " + args[1])
    state["lookups"] += 1
    answer = config["dns"][min(state["lookups"], len(config["dns"])) - 1]
    if answer:
        finish(output="10.1.2.3 STREAM " + args[1])
    finish(2)
finish(99, "Unexpected mocked command: " + repr([command, *args]))
"""


class MgmtStoragePrivateEndpointTests(unittest.TestCase):
    def run_script(self, state=(), dns=(True,), apply_exit=0, rp_type="vmss_porter"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text(
                json.dumps({"state": list(state), "dns": list(dns), "apply_exit": apply_exit})
            )
            for name in ("az", "terraform", "getent", "sleep"):
                executable = root / name
                executable.write_text(f"#!{sys.executable}\n" + MOCK_COMMAND)
                executable.chmod(0o755)
            env = {
                **os.environ,
                "MOCK_ROOT": str(root),
                "PATH": str(root) + os.pathsep + os.environ["PATH"],
                "TF_VAR_mgmt_storage_account_name": "mockstorage",
                "TF_VAR_mgmt_resource_group_name": "mockgroup",
                "TF_VAR_resource_processor_type": rp_type,
            }
            result = subprocess.run(
                ["/bin/bash", str(SCRIPT)],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            calls_file = root / "calls.jsonl"
            self.calls = (
                [json.loads(line) for line in calls_file.read_text().splitlines()] if calls_file.exists() else []
            )
            self.output = result.stdout + result.stderr
            return result

    def terraform_calls(self, subcommand):
        return [c for c in self.calls if c[0] == "terraform" and c[1] == subcommand]

    def post_apply_lookups(self):
        applied = next(i for i, c in enumerate(self.calls) if c[:2] == ["terraform", "apply"])
        return [c for c in self.calls[applied:] if c[0] == "getent"]

    def test_existing_private_endpoint_skips_targeted_apply(self):
        result = self.run_script(state=["azurerm_resource_group.core", PE_ADDRESS])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.terraform_calls("plan"), [])
        self.assertEqual(self.terraform_calls("apply"), [])

    def test_other_resource_processor_type_skips(self):
        result = self.run_script(rp_type="other")
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.calls, [])

    def test_fresh_deployment_creates_only_private_endpoint_and_waits_for_dns(self):
        result = self.run_script(dns=(True, True, True))
        self.assertEqual(result.returncode, 0, self.output)
        plans = self.terraform_calls("plan")
        self.assertEqual(len(plans), 1)
        self.assertIn(f"-target={PE_ADDRESS}", plans[0])
        self.assertEqual(len(self.terraform_calls("apply")), 1)
        self.assertEqual(len(self.post_apply_lookups()), 3)
        self.assertEqual([c for c in self.calls if c[0] == "sleep"], [["sleep", "10"]] * 2)
        self.assertIn(HOST, self.output)

    def test_transient_dns_failure_resets_and_recovers(self):
        result = self.run_script(dns=(True, False, False, True, True, True))
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.post_apply_lookups()), 6)
        self.assertIn("did not resolve", self.output)

    def test_persistent_dns_failure_is_bounded_and_reported(self):
        result = self.run_script(dns=(False,))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.post_apply_lookups()), 30)
        self.assertEqual(len([c for c in self.calls if c[0] == "sleep"]), 29)
        self.assertIn(f"{HOST} did not resolve consistently after 30 attempts", self.output)

    def test_targeted_apply_failure_stops_before_dns_wait(self):
        result = self.run_script(apply_exit=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.post_apply_lookups(), [])
        self.assertIn("apply failed", self.output)


if __name__ == "__main__":
    unittest.main()
