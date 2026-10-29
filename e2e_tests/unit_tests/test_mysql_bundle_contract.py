"""Check that the MySQL server accepts private endpoint connections only."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/mysql/terraform"


class MySQLBundleContractTests(unittest.TestCase):
    def test_server_disables_public_network_access(self):
        source = (BUNDLE / "mysql.tf").read_text()
        server = source.split('resource "azurerm_mysql_flexible_server" "mysql" {', 1)[1].split("\n}", 1)[0]
        self.assertRegex(server, r'\n  public_network_access\s*=\s*"Disabled"\n')

    def test_provider_supports_the_public_network_access_argument(self):
        # azurerm added public_network_access for MySQL flexible servers in the 4.x releases.
        main = (BUNDLE / "main.tf").read_text()
        version = re.search(r'source\s*=\s*"hashicorp/azurerm"\s*\n\s*version\s*=\s*"=?\s*(\d+)\.', main)
        self.assertIsNotNone(version)
        self.assertGreaterEqual(int(version.group(1)), 4)
        lock = (BUNDLE / ".terraform.lock.hcl").read_text()
        self.assertRegex(lock, r'provider "registry\.terraform\.io/hashicorp/azurerm" \{\n  version     = "4\.')
