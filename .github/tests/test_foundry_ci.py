import asyncio
import copy
import importlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest
from unittest.mock import AsyncMock, patch

from jsonschema import Draft7Validator
import yaml


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "templates/workspace_services/ai-foundry"
ACCESS_SETTINGS = ("is_exposed_externally", "local_auth_enabled")
LIFECYCLE_TEST = "test_ai_foundry_model_service_lifecycle"


class FoundryTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((BUNDLE / "template_schema.json").read_text())
        cls.porter = yaml.safe_load((BUNDLE / "porter.yaml").read_text())
        cls.parameters = {item["name"]: item for item in cls.porter["parameters"]}

    def test_access_combinations_are_valid(self):
        Draft7Validator.check_schema(self.schema)
        validator = Draft7Validator(self.schema)
        for values in itertools.product((False, True), repeat=2):
            with self.subTest(values=values):
                validator.validate(dict(zip(ACCESS_SETTINGS, values)))

    def test_access_settings_reject_non_boolean_values(self):
        validator = Draft7Validator(self.schema)
        for name in ACCESS_SETTINGS:
            for value in ("true", "false", 0, 1, None):
                with self.subTest(name=name, value=value):
                    self.assertFalse(validator.is_valid({name: value}))

    def test_schema_and_porter_defaults_agree(self):
        for name in ACCESS_SETTINGS:
            with self.subTest(name=name):
                field = self.schema["properties"][name]
                parameter = self.parameters[name]
                self.assertEqual(field["type"], "boolean")
                self.assertTrue(field["updateable"])
                self.assertIs(field["default"], False)
                self.assertEqual(parameter["type"], field["type"])
                self.assertEqual(parameter["default"], field["default"])

    def test_access_settings_reach_every_terraform_action(self):
        for action in ("install", "upgrade", "uninstall"):
            for name in ACCESS_SETTINGS:
                with self.subTest(action=action, name=name):
                    variables = self.porter[action][0]["terraform"]["vars"]
                    self.assertEqual(variables[name], "${ bundle.parameters." + name + " }")

    def test_secret_reference_is_returned_on_install_and_upgrade(self):
        output = next(item for item in self.porter["outputs"] if item["name"] == "openai_api_key_secret_id")
        self.assertEqual(output["type"], "string")
        self.assertEqual(set(output["applyTo"]), {"install", "upgrade"})
        for action in output["applyTo"]:
            names = {item["name"] for item in self.porter[action][0]["terraform"]["outputs"]}
            self.assertIn("openai_api_key_secret_id", names)

    def test_deployment_builds_and_registers_foundry(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy_tre_reusable.yml").read_text())
        for job in ("publish_bundles", "register_bundles"):
            with self.subTest(job=job):
                bundles = workflow["jobs"][job]["strategy"]["matrix"]["include"]
                self.assertIn({
                    "BUNDLE_TYPE": "workspace_service",
                    "BUNDLE_DIR": "./templates/workspace_services/ai-foundry",
                }, bundles)


class FoundryGraphTests(unittest.TestCase):
    def test_ci_runs_graph_check_after_initialisation(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/build_validation_develop.yml").read_text())
        steps = next(job["steps"] for job in workflow["jobs"].values() if "steps" in job)
        graph_index = next(i for i, step in enumerate(steps)
                           if step.get("run") == "python tests/run_dependency_graph.py")
        graph_step = steps[graph_index]
        self.assertEqual(graph_step["if"], "${{ steps.filter.outputs.foundry == 'true' }}")
        self.assertEqual(graph_step["working-directory"], str(BUNDLE.relative_to(ROOT) / "terraform"))
        self.assertTrue(any("terraform init -backend=false" in step.get("run", "")
                            and step.get("working-directory") == graph_step["working-directory"]
                            and step.get("if") == graph_step["if"] for step in steps[:graph_index]))
        filters = yaml.safe_load(next(step["with"]["filters"] for step in steps if step.get("id") == "filter"))
        self.assertIn("templates/workspace_services/ai-foundry/**", filters["foundry"])
        self.assertIn(".github/tests/**", filters["foundry"])

    def run_graph(self, remove_model_dependency=False):
        spec = importlib.util.spec_from_file_location(
            "foundry_graph_runner", BUNDLE / "terraform/tests/run_dependency_graph.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        edges = [
            ('azurerm_cognitive_account_project.default', 'azurerm_cognitive_deployment.openai'),
            ('azurerm_cognitive_account_project.default', 'azurerm_private_endpoint.ai_foundry'),
            ('azurerm_cognitive_deployment.openai', 'azurerm_cognitive_account.ai_foundry'),
            ('azurerm_cognitive_account.ai_foundry', 'azapi_resource_action.purge_ai_foundry'),
        ]
        if remove_model_dependency:
            edges.pop(0)
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            original = (BUNDLE / "terraform/main.tf").read_text()
            (source / "main.tf").write_text(original)
            (source / ".terraform.lock.hcl").write_text("# Test lock\n")
            for name in ("modules", "providers"):
                (source / ".terraform" / name).mkdir(parents=True)
            (source / ".terraform/terraform.tfstate").write_text("backend metadata")
            (source / "terraform.tfstate").write_text("resource state")
            (source / "tests").mkdir()
            (source / "tests/check_dependency_graph.py").write_text(
                (BUNDLE / "terraform/tests/check_dependency_graph.py").read_text())
            offline_paths = []

            def execute(command, **kwargs):
                if command[0] == "terraform":
                    self.assertEqual(command, ["terraform", "graph"])
                    offline = kwargs["cwd"]
                    offline_paths.append(offline)
                    self.assertEqual((offline / "main.tf").read_text(),
                                     original.replace('  backend "azurerm" {}\n', "", 1))
                    self.assertFalse((offline / "terraform.tfstate").exists())
                    self.assertFalse((offline / ".terraform/terraform.tfstate").exists())
                    for dependent, dependency in edges:
                        kwargs["stdout"].write(f'"{dependent}" -> "{dependency}";\n')
                    return subprocess.CompletedProcess(command, 0)
                self.assertEqual(Path(command[1]).name, "check_dependency_graph.py")
                return real_run(command, capture_output=True, text=True, **kwargs)

            with patch.object(runner.subprocess, "run", side_effect=execute):
                if remove_model_dependency:
                    with self.assertRaises(subprocess.CalledProcessError) as failure:
                        runner.check_graph(source)
                    self.assertIn("No dependency path", failure.exception.stderr)
                else:
                    runner.check_graph(source)
            self.assertEqual((source / "main.tf").read_text(), original)
            self.assertEqual(len(offline_paths), 1)
            self.assertFalse(offline_paths[0].exists())

    def test_default_graph_passes_without_copying_backend_or_state(self):
        self.run_graph()

    def test_missing_required_dependency_fails(self):
        self.run_graph(remove_model_dependency=True)


class FoundryLifecycleTests(unittest.TestCase):
    def run_lifecycle(self, stage=None, setting=None, value=None):
        with patch.object(sys, "path", [str(ROOT), str(ROOT / "e2e_tests"), *sys.path]):
            lifecycle = importlib.import_module("e2e_tests.test_workspace_services")
        workspace_path = "/workspaces/offline"
        service_path = workspace_path + "/workspace-services/foundry"
        properties = {}
        calls = []
        reads = 0

        async def post(payload, path, token, verify, method="POST"):
            self.assertIs(verify, True)
            calls.append((method, path, copy.deepcopy(payload)))
            if method == "POST":
                self.assertEqual(path, "/api" + workspace_path + "/workspace-services")
                self.assertEqual(payload["templateName"], lifecycle.strings.AI_FOUNDRY_SERVICE)
                properties.update(copy.deepcopy(payload["properties"]))
                # Deployment outputs supplement the inputs. No input defaults are inserted.
                properties.update(ai_foundry_id="/subscriptions/offline/accounts/foundry",
                                  openai_endpoint="https://offline.openai.azure.com/",
                                  openai_model_deployment="gpt-5.1", openai_api_key_secret_id="")
            else:
                self.assertEqual(method, "PATCH")
                self.assertEqual(path, "/api" + service_path)
                self.assertEqual(payload, {"properties": {"openai_model_capacity": 1}})
                properties.update(copy.deepcopy(payload["properties"]))
            return service_path, {}

        async def get(path, token, verify):
            nonlocal reads
            self.assertEqual(path, "/api" + service_path)
            self.assertIs(verify, True)
            reads += 1
            returned = copy.deepcopy(properties)
            if reads == stage:
                returned[setting] = value
            return {"workspaceService": {"properties": returned}}

        cleanup = AsyncMock()
        with patch.object(lifecycle, "post_resource", side_effect=post), \
                patch.object(lifecycle, "get_resource", side_effect=get), \
                patch.object(lifecycle, "get_workspace_owner_token", new=AsyncMock(return_value="offline-token")), \
                patch.object(lifecycle, "disable_and_delete_ws_resource", new=cleanup):
            invocation = lifecycle.test_ai_foundry_model_service_lifecycle(True, (workspace_path, "offline"))
            if stage:
                with self.assertRaises(AssertionError):
                    asyncio.run(invocation)
            else:
                asyncio.run(invocation)
        cleanup.assert_awaited_once_with(service_path, "offline", True)
        self.assertEqual(reads, stage or 2)
        self.assertEqual([call[0] for call in calls], ["POST"] if stage == 1 else ["POST", "PATCH"])
        supplied = calls[0][2]["properties"]
        self.assertEqual(supplied["openai_model"], "gpt-5.1 | 2025-11-13")
        self.assertEqual(supplied["openai_model_capacity"], 1)
        for name in ACCESS_SETTINGS:
            self.assertIs(supplied[name], False)

    def test_lifecycle_preserves_inputs_upgrades_and_cleans_up(self):
        self.run_lifecycle()

    def test_lifecycle_rejects_incorrect_initial_settings(self):
        for setting, value in (("openai_model", "wrong-model"), ("openai_model_capacity", 2),
                               ("is_exposed_externally", True), ("local_auth_enabled", True),
                               ("openai_api_key_secret_id", "unexpected-secret-reference")):
            with self.subTest(setting=setting):
                self.run_lifecycle(1, setting, value)

    def test_lifecycle_rejects_incorrect_upgraded_settings(self):
        for setting, value in (("is_exposed_externally", True), ("local_auth_enabled", True),
                               ("openai_api_key_secret_id", "unexpected-secret-reference"),
                               ("ai_foundry_id", "/subscriptions/changed"),
                               ("openai_endpoint", "https://changed.invalid"),
                               ("openai_model_deployment", "changed-deployment")):
            with self.subTest(setting=setting):
                self.run_lifecycle(2, setting, value)


class FoundryTestSelectionTests(unittest.TestCase):
    def collect(self, selector):
        # Collection imports the real E2E modules but never runs Azure fixtures.
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "e2e_tests")))
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", selector,
             "test_workspace_services.py", "test_workspace_service_templates.py"],
            cwd=ROOT / "e2e_tests", env=environment, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_existing_aad_selector_includes_foundry_lifecycle(self):
        self.assertIn(LIFECYCLE_TEST, self.collect("extended_aad"))

    def test_workspace_service_selector_includes_foundry_lifecycle(self):
        self.assertIn(LIFECYCLE_TEST, self.collect("workspace_services"))

    def test_focused_selector_includes_lifecycle_and_template_checks(self):
        collected = self.collect("foundry")
        self.assertIn(LIFECYCLE_TEST, collected)
        self.assertIn("test_ai_foundry_template_access_settings", collected)
        self.assertIn("test_get_workspace_service_templates[tre-workspace-service-ai-foundry]", collected)
        self.assertIn("test_get_workspace_service_template[tre-workspace-service-ai-foundry]", collected)
        self.assertNotIn("test_create_guacamole_service", collected)

    def test_smoke_checks_template_without_deploying_a_model(self):
        collected = self.collect("smoke")
        self.assertIn("test_ai_foundry_template_access_settings", collected)
        self.assertNotIn(LIFECYCLE_TEST, collected)


if __name__ == "__main__":
    unittest.main()
