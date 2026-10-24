"""Check the private storage and database settings of the Gitea workspace service."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/gitea/terraform"


def block(source, header):
    return source.split(header + " {", 1)[1].split("\n}", 1)[0]


class GiteaBundleContractTests(unittest.TestCase):
    def test_share_uses_resource_manager(self):
        # With storage_account_name, the provider uses the file endpoint. The TRE firewall blocks it
        # before the private endpoint exists and after Terraform deletes the private endpoint.
        share = block((BUNDLE / "storage.tf").read_text(), 'resource "azurerm_storage_share" "gitea"')
        self.assertRegex(share, r"\n  storage_account_id\s*=\s*azurerm_storage_account\.gitea\.id\n")
        self.assertNotIn("storage_account_name", share)

    def test_server_disables_public_network_access(self):
        server = block((BUNDLE / "mysql.tf").read_text(), 'resource "azurerm_mysql_flexible_server" "gitea"')
        self.assertRegex(server, r'\n  public_network_access\s*=\s*"Disabled"\n')
