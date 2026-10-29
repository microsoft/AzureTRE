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
CONTAINER = "/vault/backupFabrics/Azure/protectionContainers/container?api-version=2023-04-01"
OPERATION = "https://management.azure.com/vault/operations/1"

FAKE_AZ = """import json,os,sys
args=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
state=json.load(open(os.environ['STATE']))
def save():json.dump(state,open(os.environ['STATE'],'w'))
if args[0]!='rest':sys.exit(0)
method=args[args.index('--method')+1];url=args[args.index('--url')+1]
if url==os.environ['OPERATION']:
    outcome=state['outcomes'].pop(0) if len(state['outcomes'])>1 else state['outcomes'][0]
    if outcome=='ERROR':save();sys.exit(1)
    print(outcome)
    state['registered']=outcome=='Succeeded';save();sys.exit(0)
if method=='get':
    if state['get_errors']:
        state['get_errors']-=1;save();print('ERROR: (TooManyRequests) The request was throttled.',file=sys.stderr);sys.exit(1)
    if state['registered'] and '--query' in args:
        statuses=state['registration_statuses'];status=statuses.pop(0) if len(statuses)>1 else statuses[0];save();print(status);sys.exit(0)
    if state['registered']:sys.exit(0)
    print('ERROR: Not Found({"error":{"code":"BMSUserErrorContainerObjectNotFound"}})',file=sys.stderr);sys.exit(1)
if method=='put':
    if state['put_lost']:
        state['registered']=True;save();print('ERROR: (ConnectionResetError) Connection aborted.',file=sys.stderr);sys.exit(1)
    if state['put_failures']:
        state['put_failures']-=1;save();print('ERROR: (CloudInternalError) Microsoft Azure Backup encountered an internal error.',file=sys.stderr);sys.exit(1)
    if state['put_registers']:state['registered']=True;save()
    if state['header']:print("INFO: cli.azure.cli.core.util:     '"+state['header_name']+"': '"+os.environ['OPERATION']+"'",file=sys.stderr)
    sys.exit(0)
if method=='delete':
    if state['delete_failures']:
        state['delete_failures']-=1;save();print('ERROR: (CloudInternalError) Microsoft Azure Backup encountered an internal error.',file=sys.stderr);sys.exit(1)
    state['registered']=False;save();sys.exit(0)
"""


def warm_up_command():
    source = STORAGE.read_text()
    block = source.split('resource "terraform_data" "backup_registration_warm_up" {', 1)[1]
    command = block.split("<<EOT\n", 1)[1].split("\nEOT", 1)[0]
    return (
        # Terraform renders $${ as ${ in the command.
        command.replace("$${", "${")
        .replace("${self.input.subscription_id}", "subscription")
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

    def run_warm_up(
        self,
        *,
        registered=False,
        outcomes=("Failed",),
        header=True,
        get_errors=0,
        delete_failures=0,
        environment=None,
        put_failures=0,
        put_registers=False,
        header_name="Azure-AsyncOperation",
        registration_statuses=("Registered",),
        put_lost=False,
    ):
        state = self.folder / "state.json"
        state.write_text(
            json.dumps(
                {
                    "registered": registered,
                    "outcomes": list(outcomes),
                    "header": header,
                    "get_errors": get_errors,
                    "delete_failures": delete_failures,
                    "put_failures": put_failures,
                    "put_registers": put_registers,
                    "header_name": header_name,
                    "registration_statuses": list(registration_statuses),
                    "put_lost": put_lost,
                }
            )
        )
        env = (
            os.environ
            | {
                "PATH": str(self.folder) + os.pathsep + os.environ["PATH"],
                "CALLS": str(self.folder / "calls.jsonl"),
                "STATE": str(state),
                "OPERATION": OPERATION,
            }
            | (environment or {})
        )
        result = subprocess.run(["bash", "-c", warm_up_command()], env=env, capture_output=True, text=True, timeout=20)
        calls_file = self.folder / "calls.jsonl"
        calls = [json.loads(line) for line in calls_file.read_text().splitlines()] if calls_file.exists() else []
        methods = [call[call.index("--method") + 1] for call in calls if call[0] == "rest" and CONTAINER in call]
        self.calls = calls
        return result, methods, json.loads(state.read_text())

    def test_existing_registration_is_not_changed(self):
        result, methods, state = self.run_warm_up(registered=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get"])
        self.assertTrue(state["registered"])

    def test_five_failed_attempts_leave_registration_to_terraform(self):
        result, methods, state = self.run_warm_up(outcomes=["Failed"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get"] + ["put", "get"] * 5)
        self.assertFalse(state["registered"])
        self.assertIn("Registration attempt 5 ended with status Failed", result.stdout)

    def test_attempts_continue_until_one_succeeds(self):
        result, methods, state = self.run_warm_up(outcomes=["Failed", "Failed", "Succeeded"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get"] + ["put", "get"] * 3 + ["get", "delete", "get"])
        self.assertFalse(state["registered"])
        self.assertIn("Registration attempt 3 ended with status Succeeded", result.stdout)

    def test_successful_first_attempt_is_removed_for_terraform(self):
        result, methods, state = self.run_warm_up(outcomes=["Succeeded"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "get", "delete", "get"])
        self.assertFalse(state["registered"])

    def test_failed_unregister_is_sent_again(self):
        # Azure can answer the unregister with a short CloudInternalError.
        result, methods, state = self.run_warm_up(outcomes=["Succeeded"], delete_failures=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "get", "delete"] + ["get"] * 6 + ["delete", "get"])
        self.assertFalse(state["registered"])

    def test_lost_put_response_waits_for_the_registration_before_the_unregister(self):
        # Azure accepted the PUT, but the response was lost, so the step sees an error.
        result, methods, state = self.run_warm_up(put_lost=True, registration_statuses=["Registering", "Registered"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "get", "get", "delete", "get"])
        self.assertFalse(state["registered"])
        self.assertIn("Registration attempt 1 ended with status Rejected", result.stdout)

    def test_lost_put_response_stops_the_step_while_the_registration_runs(self):
        result, methods, state = self.run_warm_up(put_lost=True, registration_statuses=["Registering"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("delete", methods)
        self.assertTrue(state["registered"])
        self.assertIn("does not unregister a registration that has not ended", result.stderr)

    def test_lasting_unregister_failure_names_the_recovery(self):
        result, methods, state = self.run_warm_up(outcomes=["Succeeded"], delete_failures=100)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(methods.count("delete"), 10)
        self.assertTrue(state["registered"])
        self.assertIn("Unregister the storage account in the vault, then update the workspace again", result.stderr)

    def test_read_error_does_not_change_an_existing_registration(self):
        result, methods, state = self.run_warm_up(registered=True, get_errors=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "get"])
        self.assertTrue(state["registered"])

    def test_lasting_read_error_stops_the_step(self):
        result, methods, state = self.run_warm_up(get_errors=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(methods, ["get"] * 3)
        self.assertIn("Could not read the backup registration", result.stderr)

    def test_attempt_without_a_final_status_stops_the_step(self):
        result, methods, _ = self.run_warm_up(outcomes=["InProgress"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(methods, ["get", "put"])
        self.assertIn("did not end within 10 minutes", result.stderr)

    def test_failed_status_read_is_read_again(self):
        result, methods, state = self.run_warm_up(outcomes=["ERROR", "InProgress", "Succeeded"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "get", "delete", "get"])
        self.assertFalse(state["registered"])

    def test_login_uses_the_cloud_and_the_managed_identity_by_default(self):
        result, _, _ = self.run_warm_up(registered=True, environment={"AZURE_ENVIRONMENT": "AzureUSGovernment"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls[0], ["cloud", "set", "--name", "AzureUSGovernment"])
        self.assertEqual(self.calls[1][:2], ["login", "--identity"])

    def test_login_uses_the_service_principal_without_a_managed_identity(self):
        environment = {
            "ARM_USE_MSI": "false",
            "ARM_CLIENT_ID": "client",
            "ARM_CLIENT_SECRET": "secret",
            "ARM_TENANT_ID": "tenant",
        }
        result, _, _ = self.run_warm_up(registered=True, environment=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls[0], ["cloud", "set", "--name", "AzureCloud"])
        self.assertEqual(
            self.calls[1],
            [
                "login",
                "--service-principal",
                "--username",
                "client",
                "--password",
                "secret",
                "--tenant",
                "tenant",
                "--output",
                "none",
            ],
        )

    def test_accepted_put_without_an_operation_stops_the_step(self):
        result, methods, _ = self.run_warm_up(header=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(methods, ["get", "put"] + ["get"] * 60)
        self.assertIn("has no operation to follow", result.stderr)
        self.assertIn("The last status was Unknown", result.stderr)

    def test_accepted_put_without_an_operation_waits_for_the_registration(self):
        # The container can exist before its registration ends. The step must not unregister it then.
        result, methods, state = self.run_warm_up(
            header=False, put_registers=True, registration_statuses=["Registering", "Registering", "Registered"]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "get", "get", "get", "get", "delete", "get"])
        self.assertFalse(state["registered"])

    def test_accepted_put_without_an_operation_stops_while_the_registration_runs(self):
        result, methods, state = self.run_warm_up(
            header=False, put_registers=True, registration_statuses=["Registering"]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("delete", methods)
        self.assertTrue(state["registered"])
        self.assertIn("The last status was Registering", result.stderr)

    def test_accepted_put_without_an_operation_continues_when_registered(self):
        result, methods, state = self.run_warm_up(header=False, put_registers=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "get", "get", "delete", "get"])
        self.assertFalse(state["registered"])

    def test_rejected_puts_wait_and_leave_registration_to_terraform(self):
        result, methods, state = self.run_warm_up(put_failures=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get"] + ["put", "get"] * 5)
        self.assertFalse(state["registered"])
        self.assertIn("Registration attempt 5 ended with status Rejected", result.stdout)

    def test_operation_header_is_read_in_any_case(self):
        result, methods, state = self.run_warm_up(outcomes=["Succeeded"], header_name="azure-asyncoperation")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(methods, ["get", "put", "get", "get", "delete", "get"])
        self.assertFalse(state["registered"])

    def test_terraform_registration_waits_for_the_warm_up(self):
        block = STORAGE.read_text().split('resource "azurerm_backup_container_storage_account" "storage_account" {', 1)[
            1
        ]
        block = block.split("\nresource ", 1)[0]
        self.assertRegex(block, r"depends_on\s*=\s*\[\s*terraform_data\.backup_registration_warm_up\s*\]")
