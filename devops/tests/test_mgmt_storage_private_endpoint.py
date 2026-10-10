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
if command == "timeout":
    os.execvp(args[1], args[1:])
if command == "az" and args[:3] == ["storage", "account", "show"]:
    finish(output="https://" + config["host"] + "/")
if command == "terraform" and args[:2] == ["state", "list"]:
    finish(output="\n".join(config["state"]))
if command == "terraform" and args[:2] == ["state", "pull"]:
    ready = config["backend"][min(state["lookups"], len(config["backend"])) - 1]
    finish(0 if ready else 1, "SECRET_STATE_CONTENT" if ready else "backend unavailable")
if command == "terraform" and args[0] == "plan":
    finish()
if command == "terraform" and args[0] == "apply":
    finish(config["apply_exit"], "apply failed" if config["apply_exit"] else "")
if command == "dig":
    if "CNAME" not in args:
        finish(output="DNS diagnostics")
    state["lookups"] += 1
    alias = config["cnames"][min(state["lookups"], len(config["cnames"])) - 1]
    finish(output=alias)
if command == "getent":
    if state["lookups"] == 0:
        finish(output="20.0.0.1 STREAM " + args[1])
    answer = config["dns"][min(state["lookups"], len(config["dns"])) - 1]
    if answer:
        finish(output="10.1.2.3 STREAM " + args[1])
    finish(2)
finish(99, "Unexpected mocked command: " + repr([command, *args]))
"""


class MgmtStoragePrivateEndpointTests(unittest.TestCase):
    def run_script(
        self, state=(), dns=(True,), apply_exit=0, rp_type="vmss_porter", cnames=None, backend=(True,), host=HOST
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "state": list(state),
                        "dns": list(dns),
                        "apply_exit": apply_exit,
                        "cnames": cnames or [host.replace(".", ".privatelink.", 1) + "."],
                        "backend": backend,
                        "host": host,
                    }
                )
            )
            for name in ("az", "terraform", "getent", "sleep", "dig", "timeout"):
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

    def dns_attempts(self):
        return [c for c in self.calls if c[0] == "dig" and "CNAME" in c]

    def test_existing_private_endpoint_skips_targeted_apply(self):
        result = self.run_script(state=["azurerm_resource_group.core", PE_ADDRESS])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.terraform_calls("plan"), [])
        self.assertEqual(self.terraform_calls("apply"), [])
        self.assertEqual(len(self.dns_attempts()), 3)
        self.assertEqual(len([c for c in self.calls if c[:3] == ["terraform", "state", "pull"]]), 3)

    def test_rerun_still_fails_if_dns_never_becomes_ready(self):
        result = self.run_script(state=[PE_ADDRESS], dns=(False,))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.terraform_calls("apply"), [])
        self.assertEqual(len(self.dns_attempts()), 30)

    def test_stale_public_alias_cannot_satisfy_readiness(self):
        result = self.run_script(cnames=["blob.storage.example.test."])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.dns_attempts()), 30)
        self.assertEqual([c for c in self.calls if c[:3] == ["terraform", "state", "pull"]], [])
        self.assertIn("expected alias not observed", self.output)

    def test_stale_alias_resets_consecutive_successes(self):
        private = "mockstorage.privatelink.blob.core.windows.net."
        result = self.run_script(cnames=[private, "stale.example.test.", private, private, private])
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.dns_attempts()), 5)

    def test_another_accounts_private_alias_is_rejected(self):
        result = self.run_script(cnames=["other.privatelink.blob.core.windows.net."])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.dns_attempts()), 30)

    def test_alias_uses_actual_cloud_endpoint_and_dns_case_insensitivity(self):
        result = self.run_script(
            host="mockstorage.blob.core.usgovcloudapi.net",
            cnames=["MOCKSTORAGE.PRIVATELINK.BLOB.CORE.USGOVCLOUDAPI.NET."],
        )
        self.assertEqual(result.returncode, 0, self.output)

    def test_backend_failure_resets_and_recovers_without_logging_state(self):
        result = self.run_script(backend=(True, False, True, True, True))
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.dns_attempts()), 5)
        self.assertIn("backend read failed", self.output)
        self.assertNotIn("SECRET_STATE_CONTENT", self.output)

    def test_persistent_backend_failure_is_bounded_and_has_dns_diagnostics(self):
        result = self.run_script(backend=(False,))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.dns_attempts()), 30)
        self.assertIn("backend unavailable", self.output)
        self.assertTrue(any(c[0] == "dig" and "@168.63.129.16" in c for c in self.calls))

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
        self.assertEqual(len(self.dns_attempts()), 3)
        self.assertEqual([c for c in self.calls if c[0] == "sleep"], [["sleep", "10"]] * 2)
        self.assertIn(HOST, self.output)

    def test_transient_dns_failure_resets_and_recovers(self):
        result = self.run_script(dns=(True, False, False, True, True, True))
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(len(self.dns_attempts()), 6)
        self.assertIn("did not resolve", self.output)

    def test_persistent_dns_failure_is_bounded_and_reported(self):
        result = self.run_script(dns=(False,))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.dns_attempts()), 30)
        self.assertEqual(len([c for c in self.calls if c[0] == "sleep"]), 29)
        self.assertIn(f"{HOST} did not become ready after 30 attempts", self.output)

    def test_targeted_apply_failure_stops_before_dns_wait(self):
        result = self.run_script(apply_exit=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.dns_attempts(), [])
        self.assertIn("apply failed", self.output)


if __name__ == "__main__":
    unittest.main()
