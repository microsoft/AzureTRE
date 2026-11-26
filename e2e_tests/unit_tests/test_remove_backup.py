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
WORKSPACE = "workspace-1234"
# The names of the vault and the storage account have only the last four characters of the workspace ID.
OTHER_WORKSPACE = "another-workspace-1234"
OTHER = [
    "azurerm_private_endpoint.stgfilepe",
    "azurerm_key_vault.kv",
    "module.network.azurerm_virtual_network.ws",
    "terraform_data.backup_registration_warm_up[0]",
]
# Azure Backup puts a delete lock on the storage account. Azure writes parts of a lock ID in lower case.
LOCK = (
    "/subscriptions/sub/resourcegroups/rg-tre-ws-1234/providers/Microsoft.Storage/storageAccounts/stgws1234"
    "/providers/Microsoft.Authorization/locks/AzureBackupProtectionLock"
)

FAKE_AZ = """import json,os,sys
args=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f:f.write(json.dumps(args)+'\\n')
state=json.load(open(os.environ['AZ_STATE']))
command=' '.join(args[:3])
if command.startswith('backup vault show'):
    if not state['vault']:print('(ResourceNotFound) The Resource was not found.',file=sys.stderr);sys.exit(1)
    if '--query' in args:print(state['vault_owner'])
    sys.exit(0)
if command.startswith('backup item list'):
    if 'AzureStorage' in args:
        print('StorageContainer;storage;rg;stgws1234\\tAzureFileShare;share\\t'+state['item']+'\\t'+str(state['deferred']))
    sys.exit(0)
if command.startswith('backup protection disable'):
    if args[args.index('--delete-backup-data')+1]=='true':state['deferred']=True
    else:state['item']='ProtectionStopped'
    json.dump(state,open(os.environ['AZ_STATE'],'w'));sys.exit(0)
if command.startswith('account show'):print('sub');sys.exit(0)
if command.startswith('resource show'):
    if not state['account']:print('(ResourceNotFound) The Resource was not found.',file=sys.stderr);sys.exit(1)
    if '--query' in args:print(state['account_owner'])
    sys.exit(0)
if command.startswith('lock list'):print(os.environ['LOCK']);sys.exit(0)
if command.startswith('storage account update') and state['update_fails']:
    print('(AuthorizationFailed) The client has no authorization.',file=sys.stderr);sys.exit(1)
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
            "LOCK": LOCK,
        }

    def run_script(
        self,
        delete_backups,
        vault=True,
        account=True,
        item="Protected",
        deferred=False,
        update_fails=False,
        vault_owner=WORKSPACE,
        account_owner=WORKSPACE,
    ):
        state = {
            "vault": vault,
            "account": account,
            "item": item,
            "deferred": deferred,
            "update_fails": update_fails,
            "vault_owner": vault_owner,
            "account_owner": account_owner,
        }
        (self.folder / "az.json").write_text(json.dumps(state))
        (self.folder / "calls.jsonl").unlink(missing_ok=True)
        (self.folder / "state.txt").write_text("\n".join(BACKUP + STORAGE + OTHER + ["azurerm_resource_group.ws"]))
        arguments = ["rg-mgmt", "stmgmt", "tfstate", "tre", WORKSPACE, "true", delete_backups, ""]
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

    @staticmethod
    def network_updates(calls):
        return [call for call in calls if call[:3] == ["storage", "account", "update"]]

    def test_retained_backups_set_the_retained_account_to_deny(self):
        # With local debugging on, the network rules of the workspace allow all networks.
        result, _, calls = self.run_script("false")
        self.assertEqual(result.returncode, 0, result.stderr)
        [update] = self.network_updates(calls)
        self.assertTrue(update[update.index("--ids") + 1].endswith("/storageAccounts/stgws1234"))
        self.assertEqual(update[update.index("--default-action") + 1], "Deny")
        self.assertEqual(update[update.index("--bypass") + 1], "AzureServices")

    def test_a_failed_change_to_deny_keeps_the_terraform_state(self):
        # The account must have Deny before Terraform stops the management of its network rules.
        result, state, _ = self.run_script("false", update_fails=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Deny", result.stderr)
        self.assertEqual(state, set(BACKUP + STORAGE + OTHER + ["azurerm_resource_group.ws"]))

    def test_deleted_backups_do_not_change_the_network_rules(self):
        result, _, calls = self.run_script("true")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.network_updates(calls), [])

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

    def test_the_share_requests_have_no_resource_manager_host(self):
        # A URL without a host uses the Resource Manager endpoint of the cloud that the Azure CLI uses.
        result, _, calls = self.run_script("true")
        self.assertEqual(result.returncode, 0, result.stderr)
        urls = [call[4] for call in calls if call[0] == "rest" and "/fileServices/default/shares" in call[4]]
        self.assertEqual(len(urls), 2)
        for url in urls:
            self.assertTrue(url.startswith("/subscriptions/sub/resourceGroups/rg-tre-ws-1234/"), url)

    @staticmethod
    def disables(calls):
        return [
            call[call.index("--delete-backup-data") + 1]
            for call in calls
            if call[:3] == ["backup", "protection", "disable"]
        ]

    def test_each_item_is_stopped_one_time(self):
        for delete_backups in ("false", "true"):
            with self.subTest(delete_backups=delete_backups):
                result, _, calls = self.run_script(delete_backups)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.disables(calls), [delete_backups])

    def test_deleted_backups_delete_the_data_of_an_item_that_an_earlier_retain_stopped(self):
        # An earlier delete with retained backups, or an operator, can have stopped the item and kept its data.
        result, _, calls = self.run_script("true", item="ProtectionStopped")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.disables(calls), ["true"])

    def test_retained_backups_do_not_change_a_stopped_item(self):
        result, _, calls = self.run_script("false", item="ProtectionStopped")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.disables(calls), [])

    def test_an_item_in_soft_delete_is_not_changed(self):
        result, _, calls = self.run_script("true", item="ProtectionStopped", deferred=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.disables(calls), [])

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

    @staticmethod
    def changes(calls):
        """Return the calls that change a backup item, a lock, a share, the vault or the network rules."""
        return [
            call
            for call in calls
            if call[:3] in (["backup", "protection", "disable"], ["backup", "container", "unregister"])
            or call[:2] == ["lock", "delete"]
            or call[:3] == ["rest", "--method", "delete"]
            or call[:3] == ["storage", "account", "update"]
        ]

    def test_a_vault_of_another_workspace_is_not_changed(self):
        for delete_backups in ("false", "true"):
            with self.subTest(delete_backups=delete_backups):
                result, state, calls = self.run_script(delete_backups, vault_owner=OTHER_WORKSPACE)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"tre_workspace_id={OTHER_WORKSPACE}", result.stderr)
                self.assertEqual(self.changes(calls), [])
                self.assertNotIn(["lock", "list"], [call[:2] for call in calls])
                self.assertEqual(state, set(BACKUP + STORAGE + OTHER + ["azurerm_resource_group.ws"]))

    def test_a_storage_account_of_another_workspace_keeps_its_locks_and_shares(self):
        # An earlier delete removed the vault, so only the storage account shows the owner.
        result, _, calls = self.run_script("true", vault=False, account_owner=OTHER_WORKSPACE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"tre_workspace_id={OTHER_WORKSPACE}", result.stderr)
        self.assertEqual(self.changes(calls), [])
        self.assertNotIn(["lock", "list"], [call[:2] for call in calls])

    def test_a_storage_account_of_another_workspace_is_not_changed_when_the_vault_exists(self):
        # The vault passes its check. The script must read the owner of the account before the first change,
        # because the steps after the vault check delete the locks of the account.
        for delete_backups in ("false", "true"):
            for vault_owner in (WORKSPACE, ""):
                with self.subTest(delete_backups=delete_backups, vault_owner=vault_owner):
                    result, state, calls = self.run_script(
                        delete_backups, vault_owner=vault_owner, account_owner=OTHER_WORKSPACE
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"tre_workspace_id={OTHER_WORKSPACE}", result.stderr)
                    self.assertEqual(self.changes(calls), [])
                    self.assertEqual(state, set(BACKUP + STORAGE + OTHER + ["azurerm_resource_group.ws"]))

    def test_the_backup_lock_of_the_workspace_storage_account_is_deleted(self):
        for delete_backups in ("false", "true"):
            with self.subTest(delete_backups=delete_backups):
                result, _, calls = self.run_script(delete_backups)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([call[3] for call in calls if call[:2] == ["lock", "delete"]], [LOCK])

    def test_resources_without_the_workspace_tag_pass(self):
        # Terraform does not update the tags, so a resource from an earlier version can have no tag.
        for owner in ("", WORKSPACE.upper()):
            with self.subTest(owner=owner):
                result, _, calls = self.run_script("true", vault_owner=owner, account_owner=owner)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(self.deletes(calls, "/fileServices/default/shares/")), 1)

    def test_a_repeated_delete_without_the_storage_account_does_nothing(self):
        result, _, calls = self.run_script("true", vault=False, account=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.deletes(calls, "/fileServices/default/shares/"), [])
        self.assertNotIn(["lock", "list"], [call[:2] for call in calls])
