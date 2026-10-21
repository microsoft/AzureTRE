"""Check that App Insights joins the private link scope after its private endpoint exists."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "core/terraform/azure-monitor/azure-monitor.tf",
    "templates/workspaces/base/terraform/azure-monitor/azure-monitor.tf",
)


def block(source, header):
    return source.split(header, 1)[1].split("\nresource ", 1)[0]


class AppInsightsPrivateLinkTests(unittest.TestCase):
    def test_app_insights_link_waits_for_the_private_endpoint(self):
        for path in FILES:
            with self.subTest(path=path):
                source = (ROOT / path).read_text()
                link = block(source, 'resource "azurerm_monitor_private_link_scoped_service" "ampls_app_insights" {')
                endpoint = block(source, 'resource "azurerm_private_endpoint" "azure_monitor_private_endpoint" {')
                self.assertRegex(
                    link, r"depends_on\s*=\s*\[\s*azurerm_private_endpoint\.azure_monitor_private_endpoint,?\s*\]"
                )
                self.assertNotIn("ampls_app_insights", endpoint)

    def test_existing_deployments_replace_the_link(self):
        for path in FILES:
            with self.subTest(path=path):
                link = block(
                    (ROOT / path).read_text(),
                    'resource "azurerm_monitor_private_link_scoped_service" "ampls_app_insights" {',
                )
                name = re.search(r'^\s*name\s*=\s*"([^"]+)"', link, re.MULTILINE).group(1)
                self.assertNotEqual(name, "ampls-app-insights-service")
