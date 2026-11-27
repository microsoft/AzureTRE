"""Make sure that the template storage accounts keep their network rules inline."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
RULES = "azurerm_storage_account_network_rules"
REMOVED = re.compile(r"^removed \{\n(.*?)^\}", re.MULTILINE | re.DOTALL)
ACCOUNT = re.compile(r'^resource "azurerm_storage_account" "(\w+)" \{\n(.*?)^\}', re.MULTILINE | re.DOTALL)
INLINE_RULES = re.compile(r"^  network_rules \{\n(.*?)^  \}", re.MULTILINE | re.DOTALL)


def terraform_files():
    return sorted((ROOT / "templates").rglob("*.tf"))


class StorageNetworkRulesTests(unittest.TestCase):
    def test_no_separate_network_rules_resource(self):
        found = [str(path.relative_to(ROOT)) for path in terraform_files() if f'resource "{RULES}"' in path.read_text()]
        self.assertEqual(found, [])

    def test_removed_network_rules_are_not_destroyed(self):
        blocks = [
            (path, block)
            for path in terraform_files()
            for block in REMOVED.findall(path.read_text())
            if f"from = {RULES}." in block
        ]
        self.assertEqual(len(blocks), 3)
        for path, block in blocks:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertRegex(block, r"lifecycle \{\s*destroy = false\s*\}")

    def test_accounts_with_removed_rules_set_them_inline(self):
        paths = [path for path in terraform_files() if f"from = {RULES}." in path.read_text()]
        self.assertEqual(len(paths), 3)
        for path in paths:
            accounts = ACCOUNT.findall(path.read_text())
            self.assertTrue(accounts, path)
            for name, body in accounts:
                with self.subTest(path=str(path.relative_to(ROOT)), account=name):
                    rules = INLINE_RULES.search(body)
                    self.assertIsNotNone(rules)
                    self.assertIn("default_action", rules.group(1))


if __name__ == "__main__":
    unittest.main()
