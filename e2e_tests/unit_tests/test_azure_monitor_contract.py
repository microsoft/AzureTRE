"""Check the order of Azure Monitor private link scope changes and the private endpoint."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
CORE = "core/terraform/azure-monitor/azure-monitor.tf"
WORKSPACE = "templates/workspaces/base/terraform/azure-monitor/azure-monitor.tf"
FILES = (CORE, WORKSPACE)
LINKS = (
    "azurerm_monitor_private_link_scoped_service.ampls_app_insights",
    "azurerm_monitor_private_link_scoped_service.ampls_log_anaytics",
)
ENDPOINT = "azurerm_private_endpoint.azure_monitor_private_endpoint"
WAIT = "terraform_data.ampls_endpoint_update_wait"


def read(path):
    # A comment does not change the order, so a depends_on in a comment line must not count.
    return re.sub(r"(?m)^\s*#.*\n", "", (ROOT / path).read_text())


def header(address):
    kind, label = address.split(".")
    return f'resource "{kind}" "{label}" {{'


def block(source, address):
    body = source.split(header(address), 1)[1]
    # terraform fmt puts the closing brace of a top-level block in the first column.
    return body[: re.search(r"(?m)^}", body).start()]


def waits_for(source, address, target):
    found = re.search(r"depends_on\s*=\s*\[([^\]]*)\]", block(source, address))
    names = re.findall(r"\w+\.\w+", found.group(1)) if found else []
    return target in names or any(waits_for(source, name, target) for name in names if header(name) in source)


class PrivateLinkScopeOrderTests(unittest.TestCase):
    def test_links_wait_for_the_private_endpoint(self):
        # App Insights rejects ingestion through a private endpoint that Azure creates after its link.
        for path in FILES:
            source = read(path)
            for link in LINKS:
                with self.subTest(path=path, link=link):
                    self.assertTrue(waits_for(source, link, ENDPOINT))
                    self.assertNotIn(link, block(source, ENDPOINT))


class WorkspaceEndpointUpdateTests(unittest.TestCase):
    def test_scope_changes_wait_for_the_endpoint_update(self):
        source = read(WORKSPACE)
        for link in LINKS:
            with self.subTest(link=link):
                self.assertTrue(waits_for(source, link, WAIT))
        self.assertTrue(waits_for(source, WAIT, ENDPOINT))

    def test_destroy_waits_longer_than_the_measured_updates(self):
        source = read(WORKSPACE)
        wait = block(source, WAIT)
        self.assertRegex(wait, r"when\s*=\s*destroy")
        # Azure runs one endpoint update of up to 132 seconds for both unlinks, or one update of up to
        # 90 seconds for each unlink, one after the other. The measured total stayed below 3 minutes.
        unlinks = source.count('resource "azurerm_monitor_private_link_scoped_service"')
        self.assertGreater(int(re.search(r'command\s*=\s*"sleep (\d+)"', wait).group(1)), unlinks * 90)
