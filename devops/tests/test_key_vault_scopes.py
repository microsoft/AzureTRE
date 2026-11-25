"""Make sure that the shared service identities read only their own Key Vault secrets."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
# Each of these identities reads a fixed list of secrets from the core Key Vault.
FILES = (
    ROOT / "templates/shared_services/gitea/terraform/gitea-webapp.tf",
    ROOT / "templates/shared_services/sonatype-nexus-vm/terraform/vm.tf",
)
ASSIGNMENT = re.compile(r'^resource "azurerm_role_assignment" "(\w+)" \{(\n.*?)^\}', re.MULTILINE | re.DOTALL)
VAULT_SCOPE = re.compile(r"\n  scope\s*=\s*data\.azurerm_key_vault\.\w+\.id\n")


class KeyVaultScopeTests(unittest.TestCase):
    def test_secret_roles_are_not_on_the_whole_vault(self):
        for path in FILES:
            roles = [
                (name, body)
                for name, body in ASSIGNMENT.findall(path.read_text())
                if '"Key Vault Secrets User"' in body
            ]
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(roles)
            for name, body in roles:
                with self.subTest(path=str(path.relative_to(ROOT)), role=name):
                    self.assertNotRegex(body, VAULT_SCOPE)
                    self.assertIn("for_each = {", body)


if __name__ == "__main__":
    unittest.main()
