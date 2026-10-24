"""Check that the backup module gets the workspace encryption settings as inputs."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "templates/workspaces/base/terraform"


class BackupModuleContractTests(unittest.TestCase):
    def test_module_does_not_refer_to_workspace_resources(self):
        # Terraform validate accepts such a reference in a dynamic block. The plan fails when the block is used.
        for path in (WORKSPACE / "backup").glob("*.tf"):
            with self.subTest(file=path.name):
                self.assertNotRegex(path.read_text(), r"azurerm_(user_assigned_identity|key_vault_key)\.")

    def test_workspace_passes_the_encryption_identity_and_key(self):
        source = (WORKSPACE / "workspace.tf").read_text()
        module = source.split('module "backup" {', 1)[1].split("\n}", 1)[0]
        self.assertRegex(
            module, r"encryption_identity_id\s*=.*azurerm_user_assigned_identity\.encryption_identity\[0\]\.id"
        )
        self.assertRegex(module, r"encryption_key_id\s*=.*azurerm_key_vault_key\.encryption_key\[0\]\.versionless_id")
        variables = (WORKSPACE / "backup/variables.tf").read_text()
        for name in ("encryption_identity_id", "encryption_key_id"):
            self.assertRegex(variables, rf'variable "{re.escape(name)}"')
