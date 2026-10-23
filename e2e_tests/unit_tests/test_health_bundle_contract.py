"""Check the private network settings of the Health bundle."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/health-services/terraform"


def block(source, header):
    return source.split(header + " {", 1)[1].split("\n}", 1)[0]


class HealthBundleContractTests(unittest.TestCase):
    def test_endpoint_is_replaced_when_the_services_change(self):
        # Azure does not always add a DNS record for a service that joins after the endpoint.
        source = (BUNDLE / "main.tf").read_text()
        services = block(source, 'resource "terraform_data" "private_endpoint_services"')
        self.assertRegex(services, r"\n    fhir\s*=\s*var\.deploy_fhir\n")
        self.assertRegex(services, r"\n    dicom\s*=\s*var\.deploy_dicom\n")
        endpoint = block(source, 'resource "azurerm_private_endpoint" "health_services_private_endpoint"')
        self.assertRegex(endpoint, r"replace_triggered_by\s*=\s*\[terraform_data\.private_endpoint_services\]")

    def test_dicom_public_network_access_is_off(self):
        # The provider turns it on unless the bundle sets it.
        source = (BUNDLE / "main.tf").read_text()
        dicom = block(source, 'resource "azurerm_healthcare_dicom_service" "dicom"')
        self.assertRegex(dicom, r"\n  public_network_access_enabled\s*=\s*false\n")
