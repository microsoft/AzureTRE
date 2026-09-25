"""Workspace governance used by Foundry, in the existing template test suite."""

import asyncio
import base64
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import AsyncMock, Mock, patch

from jsonschema import Draft202012Validator
import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "templates/workspaces/base"


class WorkspaceResourcePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((BASE / "template_schema.json").read_text())
        cls.field = cls.schema["properties"]["blocked_resource_types"]
        cls.porter = yaml.safe_load((BASE / "porter.yaml").read_text())

    def test_setting_is_optional_updateable_and_disabled_by_default(self):
        Draft202012Validator.check_schema(self.schema)
        self.assertNotIn("blocked_resource_types", self.schema["required"])
        self.assertEqual(self.field["default"], [])
        self.assertTrue(self.field["updateable"])
        self.assertTrue(self.field["uniqueItems"])
        parameter = next(item for item in self.porter["parameters"] if item["name"] == "blocked_resource_types")
        self.assertEqual(parameter["type"], "string")
        self.assertEqual(json.loads(base64.b64decode(parameter["default"])), [])

    def test_valid_resource_types(self):
        validator = Draft202012Validator(self.field)
        for value in ([], ["Microsoft.Bing/accounts"],
                      ["Microsoft.Bing/accounts", "Microsoft.Search/searchServices"],
                      ["Microsoft.CognitiveServices/accounts/projects/connections"]):
            with self.subTest(value=value):
                validator.validate(value)

    def test_rejects_invalid_and_duplicate_types(self):
        validator = Draft202012Validator(self.field)
        for value in (None, "Microsoft.Bing/accounts", {}, [1], [True], [None], [""],
                      ["Microsoft.Bing/*"], [" Microsoft.Bing/accounts"], ["/subscriptions/example"],
                      ["Microsoft.Bing/accounts", "Microsoft.Bing/accounts"]):
            with self.subTest(value=value):
                self.assertFalse(validator.is_valid(value))

    def test_parameter_reaches_all_terraform_actions(self):
        for action in ("install", "upgrade", "uninstall"):
            terraform = next(step["terraform"] for step in self.porter[action] if "terraform" in step)
            self.assertEqual(terraform["vars"]["blocked_resource_types"], "${ bundle.parameters.blocked_resource_types }")
        parameters = json.loads((BASE / "parameters.json").read_text())["parameters"]
        entry = next(item for item in parameters if item["name"] == "blocked_resource_types")
        self.assertEqual(entry["source"], {"env": "BLOCKED_RESOURCE_TYPES"})

    def test_workspace_owns_scope_and_decodes_complex_parameter(self):
        content = (BASE / "terraform/workspace.tf").read_text()
        self.assertIn('source                 = "./resource-policy"', content)
        self.assertIn('resource_group_id      = azurerm_resource_group.ws.id', content)
        self.assertIn('blocked_resource_types = jsondecode(base64decode(var.blocked_resource_types))', content)
        foundry = ROOT / "templates/workspace_services/ai-foundry/terraform"
        self.assertFalse(any('"resource_policy"' in path.read_text() for path in foundry.glob("*.tf")))

    def test_resource_processor_encodes_workspace_list_for_porter(self):
        spec = importlib.util.spec_from_file_location("workspace_policy_commands", ROOT / "resource_processor/helpers/commands.py")
        commands = importlib.util.module_from_spec(spec)
        logging = ModuleType("shared.logging")
        logging.logger = Mock()
        logging.shell_output_logger = Mock()
        with patch.dict(sys.modules, {"shared": ModuleType("shared"), "shared.logging": logging}):
            spec.loader.exec_module(commands)
        for action in ("install", "upgrade", "uninstall"):
            for blocked in ([], ["Microsoft.Bing/accounts"], ["Microsoft.Bing/accounts", "Microsoft.Search/searchServices"]):
                message = {"id": "synthetic", "name": self.porter["name"], "version": self.porter["version"],
                           "action": action, "parameters": {"blocked_resource_types": blocked}}
                with patch.object(commands, "get_porter_parameter_keys", AsyncMock(return_value=["blocked_resource_types"])):
                    result = asyncio.run(commands.build_porter_command({"registry_server": "synthetic.azurecr.io"}, message))
                argument = next(item for item in result[0] if item.startswith("blocked_resource_types="))
                self.assertEqual(json.loads(base64.b64decode(argument.split("=", 1)[1])), blocked)

    def test_existing_ci_covers_workspace_policy(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/build_validation_develop.yml").read_text())
        steps = next(job["steps"] for job in workflow["jobs"].values() if "steps" in job)
        filters = yaml.safe_load(next(step["with"]["filters"] for step in steps if step.get("id") == "filter"))
        self.assertIn("templates/workspaces/base/**", filters["foundry"])
        policy_path = "templates/workspaces/base/terraform/resource-policy"
        policy = next(step for step in steps if step.get("working-directory") == policy_path)
        self.assertEqual(policy["if"], "${{ steps.filter.outputs.foundry == 'true' }}")
        self.assertIn("terraform test", policy["run"])
