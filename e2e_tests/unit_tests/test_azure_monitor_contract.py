"""Check the order of Azure Monitor private link scope changes and the private endpoint."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
CORE = "core/terraform/azure-monitor/azure-monitor.tf"
WORKSPACE = "templates/workspaces/base/terraform/azure-monitor/azure-monitor.tf"
FILES = (CORE, WORKSPACE)
ENDPOINT = "azurerm_private_endpoint.azure_monitor_private_endpoint"
WAIT = "terraform_data.ampls_endpoint_update_wait"


def block(source, address):
    kind, label = address.split(".")
    return source.split(f'resource "{kind}" "{label}" {{', 1)[1].split("\nresource ", 1)[0]


def waits_for(source, address, target):
    found = re.search(r"depends_on\s*=\s*\[([^\]]*)\]", block(source, address))
    names = re.findall(r"[\w.]+", found.group(1)) if found else []
    return any(name == target or waits_for(source, name, target) for name in names)


class AppInsightsPrivateLinkTests(unittest.TestCase):
    def test_app_insights_link_waits_for_the_private_endpoint(self):
        for path in FILES:
            with self.subTest(path=path):
                source = (ROOT / path).read_text()
                self.assertTrue(
                    waits_for(source, "azurerm_monitor_private_link_scoped_service.ampls_app_insights", ENDPOINT)
                )
                self.assertNotIn("ampls_app_insights", block(source, ENDPOINT))

    def test_existing_deployments_replace_the_link(self):
        for path in FILES:
            with self.subTest(path=path):
                link = block(
                    (ROOT / path).read_text(), "azurerm_monitor_private_link_scoped_service.ampls_app_insights"
                )
                name = re.search(r'^\s*name\s*=\s*"([^"]+)"', link, re.MULTILINE).group(1)
                self.assertNotEqual(name, "ampls-app-insights-service")


class WorkspaceEndpointUpdateTests(unittest.TestCase):
    def test_scope_changes_wait_for_the_endpoint_update(self):
        source = (ROOT / WORKSPACE).read_text()
        for address in (
            "azurerm_monitor_private_link_scoped_service.ampls_app_insights",
            "azurerm_monitor_private_link_scoped_service.ampls_log_anaytics",
        ):
            with self.subTest(address=address):
                self.assertTrue(waits_for(source, address, WAIT))
        self.assertTrue(waits_for(source, WAIT, ENDPOINT))

    def test_destroy_waits_longer_than_the_measured_updates(self):
        source = (ROOT / WORKSPACE).read_text()
        wait = block(source, WAIT)
        self.assertRegex(wait, r"when\s*=\s*destroy")
        # Azure runs one endpoint update of up to 132 seconds for both unlinks, or one update of up to
        # 90 seconds for each unlink, one after the other. The measured total stayed below 3 minutes.
        unlinks = source.count('resource "azurerm_monitor_private_link_scoped_service"')
        self.assertGreater(int(re.search(r'command\s*=\s*"sleep (\d+)"', wait).group(1)), unlinks * 90)
