"""Check that CycleCloud VM actions can resolve the Terraform output."""

from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/shared_services/cyclecloud"


class CycleCloudBundleContractTests(unittest.TestCase):
    def test_vm_actions_have_a_declared_and_emitted_resource_id(self):
        manifest = yaml.safe_load((BUNDLE / "porter.yaml").read_text())
        output = next(o for o in manifest["outputs"] if o["name"] == "azure_resource_id")
        self.assertEqual(output["type"], "string")
        for action in ("install", "upgrade", "start", "stop"):
            with self.subTest(action=action):
                self.assertIn(action, output["applyTo"])
                terraform = next(step["terraform"] for step in manifest[action] if "terraform" in step)
                self.assertIn({"name": "azure_resource_id"}, terraform["outputs"])
        for action, command in (("start", "start"), ("stop", "deallocate")):
            with self.subTest(action=action):
                step = next(s["az"] for s in manifest[action] if s.get("az", {}).get("arguments") == ["vm", command])
                self.assertEqual(step["flags"]["ids"], "${ bundle.outputs.azure_resource_id }")
        output_source = (BUNDLE / "terraform/outputs.tf").read_text()
        self.assertRegex(
            output_source, r'output "azure_resource_id"\s*\{\s*value\s*=\s*azurerm_virtual_machine\.cyclecloud\.id\s*\}'
        )
        vm_source = (BUNDLE / "terraform/cyclecloud.tf").read_text()
        self.assertIsNotNone(re.search(r'resource "azurerm_virtual_machine" "cyclecloud"', vm_source))
