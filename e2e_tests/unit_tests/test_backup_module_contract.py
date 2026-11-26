"""Check that the backup module gets the workspace encryption settings as inputs."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "templates/workspaces/base/terraform"


DECLARATION = re.compile(r'^\s*(?:resource|data)\s+"(azurerm_\w+)"\s+"(\w+)"', re.MULTILINE)
REFERENCE = re.compile(r"\b(azurerm_\w+)\.(\w+)")


def undeclared_references(sources):
    """Return the resource and data references that no source of the module declares."""
    declared = {match for source in sources for match in DECLARATION.findall(source)}
    referenced = {match for source in sources for match in REFERENCE.findall(source)}
    return sorted(referenced - declared)


class BackupModuleContractTests(unittest.TestCase):
    def test_module_refers_only_to_its_own_resources(self):
        # Terraform validate accepts a reference to a workspace resource in a dynamic block.
        # The plan fails when the block is used. So each reference must have a declaration in the module.
        sources = [path.read_text() for path in sorted((WORKSPACE / "backup").glob("*.tf"))]
        self.assertTrue(sources)
        self.assertEqual(undeclared_references(sources), [])

    def test_a_reference_to_a_workspace_resource_is_found(self):
        source = 'resource "azurerm_recovery_services_vault" "vault" {\n  name = azurerm_resource_group.ws.name\n}\n'
        self.assertEqual(undeclared_references([source]), [("azurerm_resource_group", "ws")])
        self.assertEqual(
            undeclared_references(
                ['data "azurerm_client_config" "current" {}\n', "x = data.azurerm_client_config.current.id"]
            ),
            [],
        )

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
