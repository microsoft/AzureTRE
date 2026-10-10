"""Reject missing or wildcard endpoints in the repaired Databricks region."""

import json
from pathlib import Path
import unittest


class DatabricksRegionDataTests(unittest.TestCase):
    def test_switzerland_north_has_explicit_dns_and_firewall_hosts(self):
        data_path = (
            Path(__file__).resolve().parents[2]
            / "templates/workspace_services/databricks/terraform/databricks-udr.json"
        )
        region = json.loads(data_path.read_text())["switzerlandnorth"]
        for field in (
            "metastoreDomains",
            "eventHubEndpointDomains",
            "logBlobStorageDomains",
            "artifactBlobStoragePrimaryDomains",
            "artifactBlobStorageSecondaryDomains",
        ):
            with self.subTest(field=field):
                hosts = region[field]
                self.assertIsInstance(hosts, list)
                self.assertTrue(hosts, "The bundle needs at least one host for each DNS lookup or firewall rule")
                self.assertEqual(len(hosts), len(set(hosts)), "Repeated endpoints do not add coverage")
                for host in hosts:
                    self.assertIsInstance(host, str)
                    self.assertRegex(host, r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")


if __name__ == "__main__":
    unittest.main()
