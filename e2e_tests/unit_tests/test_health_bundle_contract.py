"""Check the private network settings of the Health bundle."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/health-services/terraform"


def block(source, header):
    return source.split(header + " {", 1)[1].split("\n}", 1)[0]


def version(text):
    return tuple(int(part) for part in text.split("."))


class HealthBundleContractTests(unittest.TestCase):
    def test_dns_zone_group_gets_the_dicom_zone_without_an_endpoint_change(self):
        # A zone group change in the endpoint resource also sends the whole endpoint. Azure
        # refuses this with HTTP 409 while it links a new service, so the group is separate.
        source = (BUNDLE / "main.tf").read_text()
        endpoint = block(source, 'resource "azurerm_private_endpoint" "health_services_private_endpoint"')
        self.assertNotIn("private_dns_zone_group {", endpoint)
        self.assertIn("ignore_changes = [tags, private_dns_zone_group]", endpoint)
        self.assertNotIn("replace_triggered_by", endpoint)

        group = block(source, 'resource "azapi_resource" "health_services_dns_zone_group"')
        self.assertIn("parent_id = azurerm_private_endpoint.health_services_private_endpoint.id", group)
        self.assertIn("var.deploy_dicom ? [{", group)
        self.assertIn('error_message_regex = ["AnotherOperationInProgress"]', group)
        self.assertIn("azurerm_healthcare_dicom_service.dicom", group.split("depends_on", 1)[1])

    def test_an_update_that_adds_fhir_creates_the_zone_group_again(self):
        # The FHIR record is in the zone of the workspace record, so the group body stays the same.
        source = (BUNDLE / "main.tf").read_text()
        trigger = block(source, 'resource "terraform_data" "fhir_deployed"')
        self.assertIn("input = var.deploy_fhir", trigger)
        group = block(source, 'resource "azapi_resource" "health_services_dns_zone_group"')
        self.assertIn("replace_triggered_by = [terraform_data.fhir_deployed]", group)

    def test_private_endpoint_is_created_after_the_services(self):
        # Azure fails an endpoint to a healthcare workspace without a FHIR or DICOM service.
        source = (BUNDLE / "main.tf").read_text()
        endpoint = block(source, 'resource "azurerm_private_endpoint" "health_services_private_endpoint"')
        depends_on = endpoint.split("depends_on", 1)[1]
        self.assertIn("azurerm_healthcare_fhir_service.fhir", depends_on)
        self.assertIn("azurerm_healthcare_dicom_service.dicom", depends_on)
        for header in (
            'resource "azurerm_healthcare_fhir_service" "fhir"',
            'resource "azurerm_healthcare_dicom_service" "dicom"',
        ):
            self.assertNotIn("depends_on", block(source, header))

    def test_upgrade_removes_the_zone_group_of_the_endpoint_resource(self):
        source = (BUNDLE / "main.tf").read_text()
        group = block(source, 'resource "azapi_resource" "health_services_dns_zone_group"')
        remove = block(source, 'resource "azapi_resource_action" "remove_endpoint_dns_zone_group"')
        self.assertIn('method      = "DELETE"', remove)
        self.assertIn('/privateDnsZoneGroups/private-dns-zone-group"', remove)
        self.assertIn('name      = "private-dns-zone-group"', group)
        self.assertIn("azapi_resource_action.remove_endpoint_dns_zone_group", group)
        # The old group stays until FHIR and DICOM have their changes.
        depends_on = remove.split("depends_on", 1)[1]
        self.assertIn("azurerm_healthcare_fhir_service.fhir", depends_on)
        self.assertIn("azurerm_healthcare_dicom_service.dicom", depends_on)

    def test_azapi_can_update_resources_with_the_terraform_of_the_bundle(self):
        # Before 2.9.0, azapi returns no resource identity after an update. Terraform 1.12 and
        # later keep the identity, but earlier versions stop the update with an error.
        porter = (BUNDLE.parent / "porter.yaml").read_text()
        providers = (BUNDLE / "providers.tf").read_text()
        terraform = re.search(r"- terraform:\s*\n\s*clientVersion:\s*([\d.]+)", porter).group(1)
        azapi = re.search(r'source\s*=\s*"Azure/azapi"\s*\n\s*version\s*=\s*"=\s*([\d.]+)"', providers).group(1)
        if version(terraform) < (1, 12):
            self.assertGreaterEqual(version(azapi), (2, 9, 0))

    def test_dicom_public_network_access_is_off(self):
        # The provider turns it on unless the bundle sets it.
        source = (BUNDLE / "main.tf").read_text()
        dicom = block(source, 'resource "azurerm_healthcare_dicom_service" "dicom"')
        self.assertRegex(dicom, r"\n  public_network_access_enabled\s*=\s*false\n")

    def test_role_assignments_use_the_role_names(self):
        # Azure returns the role definition ID with the subscription. The role definition data
        # source gives the ID without it, so the plan replaced each role assignment.
        roles = (BUNDLE / "roles.tf").read_text()
        self.assertNotIn("role_definition_id", roles)
        self.assertEqual(roles.count("role_definition_name"), 4)

    def test_dicom_roles_wait_for_the_endpoint_link(self):
        # Azure accepts the zone group write only after it links a new DICOM service to the endpoint.
        roles = (BUNDLE / "roles.tf").read_text()
        for name in ("researchers_dicom_data_owner", "owners_dicom_data_owner"):
            role = block(roles, f'resource "azurerm_role_assignment" "{name}"')
            self.assertIn("depends_on = [azapi_resource.health_services_dns_zone_group]", role)
