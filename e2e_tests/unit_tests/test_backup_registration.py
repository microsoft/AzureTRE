"""Run the backup registration warm-up from the base workspace Terraform against a fake Azure CLI."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
STORAGE = ROOT / "templates/workspaces/base/terraform/storage.tf"
CONTAINER = (
    "https://management.azure.com/vault/backupFabrics/Azure/protectionContainers/container?api-version=2023-04-01"
)
OPERATION = "https://management.azure.com/vault/operations/1"

FAKE_AZ = """import json,os,sys
args=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
state=json.load(open(os.environ['STATE']))
def save():json.dump(state,open(os.environ['STATE'],'w'))
if args[0]!='rest':sys.exit(0)
method=args[args.index('--method')+1];url=args[args.index('--url')+1]
if url==os.environ['OPERATION']:
    print(state['outcome'])
    state['registered']=state['outcome']=='Succeeded';save();sys.exit(0)
if method=='get':sys.exit(0 if state['registered'] else 1)
if method=='put':
    if state['header']:print("INFO: cli.azure.cli.core.util:     'Azure-AsyncOperation': '"+os.environ['OPERATION']+"'",file=sys.stderr)
    sys.exit(0)
if method=='delete':state['registered']=False;save();sys.exit(0)
"""


def warm_up_command():
    source = STORAGE.read_text()
    block = source.split('resource "terraform_data" "backup_registration_warm_up" {', 1)[1]
    command = block.split("<<EOT\n", 1)[1].split("\nEOT", 1)[0]
    return (
        command.replace("${self.input.subscription_id}", "subscription")
        .replace("${self.input.container_url}", CONTAINER)
        .replace("${self.input.storage_account_id}", "/storage/account")
    )


class BackupRegistrationWarmUpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        for name, body in (("az", FAKE_AZ), ("sleep", "")):
            path = self.folder / name
            path.write_text("#!" + sys.executable + "\n" + body)
            path.chmod(0o755)

    def run_warm_up(self, *, registered=False, outcome="Failed", header=True):
        state = self.folder / "state.json"
        state.write_text(json.dumps({"registered": registered, "outcome": outcome, "header": header}))
        env = os.environ | {
            "PATH": str(self.folder) + os.pathsep + os.environ["PATH"],
            "CALLS": str(self.folder / "calls.jsonl"),
            "STATE": str(state),
            "OPERATION": OPERATION,
        }
        result = subprocess.run(["bash", "-c", warm_up_command()], env=env, capture_output=True, text=True, timeout=20)
        calls_file = self.folder / "calls.jsonl"
        calls = [json.loads(line) for line in calls_file.read_text().splitlines()] if calls_file.exists() else []
        methods = [call[call.index("--method") + 1] for call in calls if call[0] == "rest" and CONTAINER in call]
        return result, methods, json.loads(state.read_text())

    def test_existing_registration_is_not_changed(self):
        result, methods, state = self.run_warm_up(registered=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get"])
        self.assertTrue(state["registered"])

    def test_failed_first_attempt_leaves_registration_to_terraform(self):
        result, methods, state = self.run_warm_up(outcome="Failed")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get"])
        self.assertFalse(state["registered"])
        self.assertIn("ended with status Failed", result.stdout)

    def test_successful_first_attempt_is_removed_for_terraform(self):
        result, methods, state = self.run_warm_up(outcome="Succeeded")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "delete", "get"])
        self.assertFalse(state["registered"])

    def test_missing_operation_header_waits_before_terraform(self):
        result, methods, _ = self.run_warm_up(header=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get"])
        self.assertIn("ended with status Unknown", result.stdout)

    def test_terraform_registration_waits_for_the_warm_up(self):
        block = STORAGE.read_text().split('resource "azurerm_backup_container_storage_account" "storage_account" {', 1)[
            1
        ]
        block = block.split("\nresource ", 1)[0]
        self.assertRegex(block, r"depends_on\s*=\s*\[\s*terraform_data\.backup_registration_warm_up\s*\]")
