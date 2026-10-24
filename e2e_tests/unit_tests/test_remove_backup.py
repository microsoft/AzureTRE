"""Run the base workspace backup removal script against a fake Azure CLI and Terraform."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "templates/workspaces/base/remove_backup.sh"
BACKUP = [
    "azurerm_backup_protected_file_share.file_share[0]",
    "azurerm_backup_container_storage_account.storage_account[0]",
    "module.backup[0].azurerm_backup_policy_file_share.file_share_policy",
    "module.backup[0].azurerm_backup_policy_vm.vm_policy",
    "module.backup[0].azurerm_recovery_services_vault.vault",
]
STORAGE = [
    "azurerm_storage_account.stg",
    "azapi_resource.shared_storage",
    "azurerm_storage_container.stgcontainer",
    "azurerm_storage_account_network_rules.stgrules",
    "terraform_data.wait_for_backup_cleanup[0]",
    "azurerm_user_assigned_identity.encryption_identity[0]",
    "azurerm_role_assignment.kv_encryption_key_user[0]",
    "azurerm_key_vault_key.encryption_key[0]",
]
OTHER = [
    "azurerm_private_endpoint.stgfilepe",
    "azurerm_key_vault.kv",
    "module.network.azurerm_virtual_network.ws",
    "terraform_data.backup_registration_warm_up[0]",
]

FAKE_AZ = """import json,os,sys
args=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
state=json.load(open(os.environ['AZ_STATE']))
command=' '.join(args[:3])
if command.startswith('backup vault show'):
    if state['vault']:sys.exit(0)
    print('(ResourceNotFound) The Resource was not found.',file=sys.stderr);sys.exit(1)
if command.startswith('backup item list'):
    if 'AzureStorage' in args:print('StorageContainer;storage;rg;stgws1234\\tAzureFileShare;share\\tProtected')
    sys.exit(0)
if command.startswith('account show'):print('sub');sys.exit(0)
if command.startswith('resource show'):
    if state['account']:sys.exit(0)
    print('(ResourceNotFound) The Resource was not found.',file=sys.stderr);sys.exit(1)
if args[:3]==['rest','--method','get'] and '/fileServices/default/shares' in args[4]:print('vm-shared-storage');sys.exit(0)
if args[:3]==['rest','--method','delete'] and 'Microsoft.RecoveryServices/vaults' in args[4]:
    state['vault']=False;json.dump(state,open(os.environ['AZ_STATE'],'w'))
sys.exit(0)
"""

FAKE_TERRAFORM = """import os,sys
path=os.environ['TF_STATE']
items=open(path).read().split()
if sys.argv[1:3]==['state','list']:print('\\n'.join(items))
elif sys.argv[1:3]==['state','rm']:open(path,'w').write('\\n'.join(i for i in items if i!=sys.argv[3]))
"""


class RemoveBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        bin_folder = self.folder / "bin"
        bin_folder.mkdir()
        for name, body in (("az", FAKE_AZ), ("terraform", FAKE_TERRAFORM), ("sleep", "")):
            path = bin_folder / name
            path.write_text("#!" + sys.executable + "\n" + body)
            path.chmod(0o755)
        (self.folder / "terraform").mkdir()
        shutil.copy(SCRIPT, self.folder / "remove_backup.sh")
        self.env = os.environ | {
            "PATH": str(bin_folder) + os.pathsep + os.environ["PATH"],
            "CALLS": str(self.folder / "calls.jsonl"),
            "AZ_STATE": str(self.folder / "az.json"),
            "TF_STATE": str(self.folder / "state.txt"),
        }

    def run_script(self, delete_backups, vault=True, account=True):
        (self.folder / "az.json").write_text(json.dumps({"vault": vault, "account": account}))
        (self.folder / "state.txt").write_text("\n".join(BACKUP + STORAGE + OTHER + ["azurerm_resource_group.ws"]))
        arguments = ["rg-mgmt", "stmgmt", "tfstate", "tre", "workspace-1234", "true", delete_backups, ""]
        result = subprocess.run(
            ["bash", "./remove_backup.sh", *arguments],
            cwd=self.folder,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        calls = [json.loads(line) for line in (self.folder / "calls.jsonl").read_text().splitlines()]
        return result, set((self.folder / "state.txt").read_text().split()), calls

    @staticmethod
    def deletes(calls, part):
        return [
            index for index, call in enumerate(calls) if call[:3] == ["rest", "--method", "delete"] and part in call[4]
        ]

    def test_retained_backups_keep_the_storage_that_the_recovery_points_need(self):
        result, state, calls = self.run_script("false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state, set(OTHER))
        disable = [call for call in calls if call[:3] == ["backup", "protection", "disable"]]
        self.assertTrue(disable)
        self.assertTrue(all(call[call.index("--delete-backup-data") + 1] == "false" for call in disable))

    def test_deleted_backups_leave_the_storage_to_terraform(self):
        result, state, calls = self.run_script("true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state, set(STORAGE + OTHER + ["azurerm_resource_group.ws"]))
        disable = [call for call in calls if call[:3] == ["backup", "protection", "disable"]]
        self.assertTrue(all(call[call.index("--delete-backup-data") + 1] == "true" for call in disable))

    def test_deleted_backups_delete_the_shares_with_their_leased_snapshots(self):
        # Azure Backup keeps its lease on the share snapshots after the vault delete.
        result, _, calls = self.run_script("true")
        self.assertEqual(result.returncode, 0, result.stderr)
        [vault] = self.deletes(calls, "Microsoft.RecoveryServices/vaults")
        [share] = self.deletes(calls, "/fileServices/default/shares/")
        self.assertTrue(
            calls[share][4].endswith("/shares/vm-shared-storage?api-version=2023-05-01&$include=leased-snapshots")
        )
        self.assertGreater(share, vault)

    def test_retained_backups_keep_the_shares(self):
        result, _, calls = self.run_script("false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.deletes(calls, "/fileServices/default/shares/"), [])

    def test_a_repeated_delete_without_a_vault_still_deletes_the_shares(self):
        # An earlier delete can have deleted the vault and then failed on a leased share snapshot.
        result, _, calls = self.run_script("true", vault=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.deletes(calls, "/fileServices/default/shares/")), 1)
        self.assertIn(["lock", "list"], [call[:2] for call in calls])

    def test_a_repeated_delete_without_the_storage_account_does_nothing(self):
        result, _, calls = self.run_script("true", vault=False, account=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.deletes(calls, "/fileServices/default/shares/"), [])
        self.assertNotIn(["lock", "list"], [call[:2] for call in calls])
