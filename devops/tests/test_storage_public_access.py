"""Exercise delayed storage access changes using the real shell helper."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/storage_enable_public_access.sh"

MOCK_COMMAND = r"""
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["MOCK_ROOT"])
config = json.loads((root / "config.json").read_text())
state_file = root / "state.json"
state = json.loads(state_file.read_text()) if state_file.exists() else {
    "phase": "enable", "enable_checks": 0, "disable_checks": 0,
}
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
if args[:3] == ["storage", "account", "show"]:
    finish(output="mock-storage-account-id")
if args[:3] == ["storage", "account", "update"]:
    enabled = args[args.index("--public-network-access") + 1] == "Enabled"
    state["phase"] = "enable" if enabled else "disable"
    finish()
if args[:3] == ["storage", "container", "list"]:
    phase = state["phase"]
    state[phase + "_checks"] += 1
    count = state[phase + "_checks"]
    ready_after = config[phase + "_ready_after"]
    if phase == "enable" and count < ready_after:
        finish(1, config["enable_error"])
    if phase == "disable" and count >= ready_after:
        finish(1, "AuthorizationFailure: public access disabled")
    finish(output="tfstate")
if args[:3] == ["storage", "blob", "list"]:
    finish()
finish(99, "Unexpected mocked command: " + repr([command, *args]))
"""


class StoragePublicAccessTests(unittest.TestCase):
    def run_helper(
        self,
        enable_ready_after=1,
        disable_ready_after=1,
        enable_error="AuthorizationFailure: network rules are propagating",
        command="true",
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "enable_ready_after": enable_ready_after,
                        "disable_ready_after": disable_ready_after,
                        "enable_error": enable_error,
                    }
                )
            )
            for name in ("az", "sleep"):
                executable = root / name
                executable.write_text(f"#!{sys.executable}\n" + MOCK_COMMAND)
                executable.chmod(0o755)
            result = subprocess.run(
                [
                    "/bin/bash",
                    "-c",
                    """
set -euo pipefail
source "$1" --storage-account-name mockstorage --resource-group-name mockgroup
echo DEPLOYMENT_STARTED
eval "$2"
""",
                    "storage-access-test",
                    str(SCRIPT),
                    command,
                ],
                env={**os.environ, "MOCK_ROOT": str(root), "PATH": str(root) + os.pathsep + os.environ["PATH"]},
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.state = json.loads((root / "state.json").read_text())
            self.calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
            self.output = result.stdout + result.stderr
            return result

    def assert_cleanup_attempted(self):
        updates = [call for call in self.calls if call[:4] == ["az", "storage", "account", "update"]]
        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[-1][updates[-1].index("--public-network-access") + 1], "Disabled")
        self.assertEqual(updates[-1][updates[-1].index("--default-action") + 1], "Deny")

    def assert_waits(self, count):
        waits = [call for call in self.calls if call[0] == "sleep"]
        self.assertEqual(waits, [["sleep", "10"]] * count)

    def test_ready_storage_adds_no_wait(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, self.output)
        self.assertIn("DEPLOYMENT_STARTED", self.output)
        self.assert_waits(0)
        self.assert_cleanup_attempted()

    def test_enable_can_succeed_after_old_retry_limit(self):
        result = self.run_helper(enable_ready_after=15)
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.state["enable_checks"], 15)
        self.assert_waits(14)
        self.assert_cleanup_attempted()

    def test_final_enable_attempt_can_succeed(self):
        result = self.run_helper(enable_ready_after=30)
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.state["enable_checks"], 30)
        self.assert_waits(29)
        self.assert_cleanup_attempted()

    def test_enable_timeout_blocks_deployment_and_retains_error(self):
        error = "AuthorizationFailure: network rules still block access"
        result = self.run_helper(enable_ready_after=31, enable_error=error)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("DEPLOYMENT_STARTED", self.output)
        self.assertIn("Could not enable public access for mockstorage after 30 attempts", self.output)
        self.assertIn(error, self.output)
        self.assertEqual(self.state["enable_checks"], 30)
        self.assert_waits(29)
        self.assert_cleanup_attempted()

    def test_transient_dns_error_during_readiness_can_recover(self):
        result = self.run_helper(enable_ready_after=15, enable_error="NameResolutionError: no such host")
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.state["enable_checks"], 15)
        self.assert_waits(14)
        self.assert_cleanup_attempted()

    def test_final_disable_attempt_can_succeed(self):
        result = self.run_helper(disable_ready_after=30)
        self.assertEqual(result.returncode, 0, self.output)
        self.assertEqual(self.state["disable_checks"], 30)
        self.assert_waits(29)
        self.assert_cleanup_attempted()

    def test_disable_timeout_reports_failure_without_extra_sleep(self):
        result = self.run_helper(disable_ready_after=31)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not disable public access for mockstorage after 30 attempts", self.output)
        self.assertEqual(self.state["disable_checks"], 30)
        self.assert_waits(29)
        self.assert_cleanup_attempted()

    def test_deployment_failure_preserved_after_delayed_cleanup(self):
        result = self.run_helper(disable_ready_after=15, command="exit 7")
        self.assertEqual(result.returncode, 7, self.output)
        self.assertEqual(self.state["disable_checks"], 15)
        self.assert_waits(14)
        self.assert_cleanup_attempted()


if __name__ == "__main__":
    unittest.main()
