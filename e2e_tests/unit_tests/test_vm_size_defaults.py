"""Check that each VM size default is the same in every file that sets it."""

import json
from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]


def terraform_default(path, name):
    block = (ROOT / path).read_text().split(f'variable "{name}" {{', 1)[1].split("\n}", 1)[0]
    return re.search(r'default\s*=\s*"([^"]+)"', block).group(1)


class VMSizeDefaultTests(unittest.TestCase):
    def test_resource_processor_default_is_the_same_in_each_file(self):
        default = terraform_default("core/terraform/variables.tf", "resource_processor_vmss_sku")
        sample = yaml.safe_load((ROOT / "config.sample.yaml").read_text())
        self.assertEqual(sample["tre"]["resource_processor_vmss_sku"], default)
        action = (ROOT / ".github/actions/devcontainer_run_command/action.yml").read_text()
        self.assertIn(f"&& inputs.RESOURCE_PROCESSOR_VMSS_SKU) || '{default}' }}}}", action)
        for doc in (
            "docs/tre-admins/environment-variables.md",
            "docs/tre-admins/setup-instructions/cicd-pre-deployment-steps.md",
            "docs/tre-admins/setup-instructions/workflows.md",
        ):
            with self.subTest(doc=doc):
                self.assertIn(f"Defaults to `{default}`.", (ROOT / doc).read_text())

    def test_bundle_defaults_match_their_schema(self):
        cases = (
            ("templates/shared_services/admin-vm", "admin_jumpbox_vm_sku"),
            ("templates/shared_services/sonatype-nexus-vm", "vm_size"),
            ("templates/workspace_services/azureml/user_resources/aml_compute", "vm_size"),
        )
        for folder, name in cases:
            with self.subTest(bundle=folder):
                porter = yaml.safe_load((ROOT / folder / "porter.yaml").read_text())
                parameter = next(p for p in porter["parameters"] if p["name"] == name)
                schema = json.loads((ROOT / folder / "template_schema.json").read_text())["properties"][name]
                self.assertEqual(parameter["default"], schema["default"])
                self.assertIn(schema["default"], schema["enum"])
        nexus = terraform_default("templates/shared_services/sonatype-nexus-vm/terraform/variables.tf", "vm_size")
        schema = json.loads((ROOT / "templates/shared_services/sonatype-nexus-vm/template_schema.json").read_text())
        self.assertEqual(nexus, schema["properties"]["vm_size"]["default"])
