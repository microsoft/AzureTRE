"""Check the provider versions of the Health bundle."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/health-services/terraform"


def version(text):
    return tuple(int(part) for part in text.split("."))


class HealthBundleProviderTests(unittest.TestCase):
    def test_azurerm_keeps_a_new_fhir_service_in_the_state(self):
        # Before 4.75.0, azurerm waits for Succeeded after the FHIR create and saves the ID after this
        # wait. If Azure reports Accepted, the create fails, and the state does not get the service.
        providers = (BUNDLE / "providers.tf").read_text()
        lock = (BUNDLE / ".terraform.lock.hcl").read_text()
        azurerm = re.search(r'source\s*=\s*"hashicorp/azurerm"\s*\n\s*version\s*=\s*"=\s*([\d.]+)"', providers).group(1)
        locked = re.search(r'"registry.terraform.io/hashicorp/azurerm" \{\s*version\s*=\s*"([\d.]+)"', lock).group(1)
        self.assertGreaterEqual(version(azurerm), (4, 75, 0))
        self.assertEqual(locked, azurerm)


if __name__ == "__main__":
    unittest.main()
