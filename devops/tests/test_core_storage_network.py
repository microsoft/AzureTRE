"""Make sure that the core storage account and its users work through the private endpoints."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_STORAGE = ROOT / "core/terraform/storage.tf"
NOTIFIER = ROOT / "templates/shared_services/airlock_notifier/terraform/airlock_notifier.tf"
NEXUS_VM = ROOT / "templates/shared_services/sonatype-nexus-vm/terraform/vm.tf"


def block(source, header):
    return source.split(header + " {", 1)[1].split("\n}", 1)[0]


class CoreStorageNetworkTests(unittest.TestCase):
    def test_core_storage_denies_other_networks(self):
        account = block(CORE_STORAGE.read_text(), 'resource "azurerm_storage_account" "stg"')
        rules = block(account, "  network_rules")
        self.assertIn('default_action = var.enable_local_debugging ? "Allow" : "Deny"', rules)
        self.assertIn('bypass         = ["AzureServices"]', rules)

    def test_core_storage_has_an_endpoint_for_each_service(self):
        # A Standard Logic App uses blobs, files, queues and tables of its storage account.
        source = CORE_STORAGE.read_text()
        services = re.findall(r'subresource_names\s*=\s*\["(\w+)"\]', source)
        self.assertEqual(sorted(service.lower() for service in services), ["blob", "file", "queue", "table"])
        self.assertEqual(source.count("private_connection_resource_id = azurerm_storage_account.stg.id"), 4)

    def test_notifier_uses_its_content_share_through_the_network(self):
        source = NOTIFIER.read_text()
        logic_app = block(source, 'resource "azurerm_logic_app_standard" "logic_app"')
        self.assertIn('resource "azurerm_storage_share" "logic_app_content"', source)
        self.assertIn("storage_account_share_name = azurerm_storage_share.logic_app_content.name", logic_app)
        self.assertRegex(logic_app, r'"WEBSITE_CONTENTOVERVNET"\s*=\s*"1"')
        self.assertRegex(logic_app, r"vnet_route_all_enabled\s*=\s*true")

    def test_nexus_boot_diagnostics_use_managed_storage(self):
        vm = NEXUS_VM.read_text()
        self.assertIn("boot_diagnostics {}", vm)
        self.assertNotIn("storage_account_uri", vm)


if __name__ == "__main__":
    unittest.main()
