"""Check the CycleCloud bundle outputs, VM size and network rules."""

import base64
import json
from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/shared_services/cyclecloud"


def blocks(source, opener):
    """Return the body of each block that starts with the opener, for example 'security_rule {'."""
    result = []
    for match in re.finditer(re.escape(opener), source):
        depth = 0
        for index in range(match.end() - 1, len(source)):
            depth += {"{": 1, "}": -1}.get(source[index], 0)
            if depth == 0:
                result.append(source[match.end() : index])
                break
    return result


def setting(block, name):
    match = re.search(rf"^\s*{name}\s*=\s*(.+)$", block, re.MULTILINE)
    return match.group(1).strip() if match else None


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

    def test_new_servers_use_an_offered_size_and_upgrades_keep_the_size(self):
        source = (BUNDLE / "terraform/cyclecloud.tf").read_text()
        vm = source.split('resource "azurerm_virtual_machine" "cyclecloud" {', 1)[1].split("\n}", 1)[0]
        self.assertRegex(vm, r'\n  vm_size\s*=\s*"Standard_D4s_v5"\n')
        ignored = re.search(r"lifecycle\s*\{\s*ignore_changes\s*=\s*\[([^\]]*)\]", vm)
        self.assertIsNotNone(ignored)
        self.assertIn("vm_size", [name.strip() for name in ignored.group(1).split(",")])

    def test_network_card_has_inbound_rules_for_the_core_network(self):
        source = (BUNDLE / "terraform/nsg.tf").read_text()
        (association,) = blocks(
            source, 'resource "azurerm_network_interface_security_group_association" "cyclecloud" {'
        )
        self.assertEqual(setting(association, "network_interface_id"), "azurerm_network_interface.cyclecloud.id")
        self.assertEqual(
            setting(association, "network_security_group_id"), "azurerm_network_security_group.cyclecloud.id"
        )
        (nsg,) = blocks(source, 'resource "azurerm_network_security_group" "cyclecloud" {')
        self.assertEqual(setting(nsg, "tags"), "local.tre_shared_service_tags")
        self.assertEqual(setting(nsg, "resource_group_name"), "local.core_resource_group_name")
        rules = blocks(nsg, "security_rule {")
        self.assertEqual(len(rules), 3)
        self.assertTrue(all(setting(rule, "direction") == '"Inbound"' for rule in rules))
        core = [
            r
            for r in rules
            if setting(r, "source_address_prefixes") == "data.azurerm_virtual_network.core.address_space"
        ]
        self.assertEqual(len(core), 1)
        self.assertEqual(setting(core[0], "access"), '"Allow"')
        self.assertEqual(setting(core[0], "protocol"), '"Tcp"')
        self.assertEqual(setting(core[0], "destination_port_ranges"), '["22", "443"]')
        balancer = [r for r in rules if setting(r, "source_address_prefix") == '"AzureLoadBalancer"']
        self.assertEqual([setting(r, "access") for r in balancer], ['"Allow"'])
        deny = [r for r in rules if setting(r, "access") == '"Deny"']
        self.assertEqual(len(deny), 1)
        self.assertEqual(setting(deny[0], "source_address_prefix"), '"VirtualNetwork"')
        self.assertEqual(setting(deny[0], "destination_port_range"), '"*"')
        self.assertEqual(setting(deny[0], "protocol"), '"*"')
        priorities = [int(setting(rule, "priority")) for rule in rules]
        self.assertEqual(max(priorities), 4096)
        self.assertEqual(int(setting(deny[0], "priority")), 4096)
        self.assertEqual(len(set(priorities)), len(priorities))
        vm = (BUNDLE / "terraform/cyclecloud.tf").read_text()
        self.assertRegex(vm, r"depends_on\s*=\s*\[azurerm_network_interface_security_group_association\.cyclecloud\]")

    def test_cluster_port_is_open_only_for_the_configured_ranges(self):
        source = (BUNDLE / "terraform/nsg.tf").read_text()
        (nsg,) = blocks(source, 'resource "azurerm_network_security_group" "cyclecloud" {')
        self.assertFalse(any("9443" in rule for rule in blocks(nsg, "security_rule {")))
        (dynamic,) = blocks(nsg, 'dynamic "security_rule" {')
        self.assertEqual(
            setting(dynamic, "for_each"),
            "length(local.cluster_address_spaces) > 0 ? [local.cluster_address_spaces] : []",
        )
        (content,) = blocks(dynamic, "content {")
        self.assertEqual(setting(content, "access"), '"Allow"')
        self.assertEqual(setting(content, "destination_port_range"), '"9443"')
        self.assertEqual(setting(content, "source_address_prefixes"), "security_rule.value")

    def test_cluster_address_spaces_is_an_updateable_list_that_is_empty_by_default(self):
        schema = json.loads((BUNDLE / "template_schema.json").read_text())
        prop = schema["properties"]["cluster_address_spaces"]
        self.assertEqual((prop["type"], prop["default"], prop["updateable"]), ("array", [], True))
        self.assertEqual(prop["items"]["type"], "string")
        pattern = re.compile(prop["items"]["pattern"])
        self.assertTrue(pattern.fullmatch("10.1.4.0/24"))
        for value in ("10.1.4.0", "10.1.4.0/33", "256.1.4.0/24", "10.1.4/24"):
            self.assertIsNone(pattern.fullmatch(value), value)
        manifest = yaml.safe_load((BUNDLE / "porter.yaml").read_text())
        parameter = next(p for p in manifest["parameters"] if p["name"] == "cluster_address_spaces")
        self.assertEqual(parameter["type"], "string")
        self.assertEqual(json.loads(base64.b64decode(parameter["default"])), [])
        for action in ("install", "upgrade", "uninstall"):
            with self.subTest(action=action):
                terraform = next(step["terraform"] for step in manifest[action] if "terraform" in step)
                self.assertEqual(
                    terraform["vars"]["cluster_address_spaces"], "${ bundle.parameters.cluster_address_spaces }"
                )
        self.assertIn('variable "cluster_address_spaces"', (BUNDLE / "terraform/variables.tf").read_text())
        self.assertRegex(
            (BUNDLE / "terraform/locals.tf").read_text(),
            r"cluster_address_spaces\s*=\s*jsondecode\(base64decode\(var\.cluster_address_spaces\)\)",
        )
