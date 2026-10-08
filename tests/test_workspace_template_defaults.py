import json
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_BUNDLES = ("base", "unrestricted", "airlock-import-review")
PARAM_NAME = "create_aad_groups"


def _get_porter_default(workspace_dir: Path) -> bool:
    porter_yaml_path = workspace_dir / "porter.yaml"
    porter = yaml.safe_load(porter_yaml_path.read_text(encoding="utf-8"))
    parameter = next(
        (parameter for parameter in porter["parameters"] if parameter["name"] == PARAM_NAME),
        None,
    )
    if parameter is None:
        raise AssertionError(f"Parameter '{PARAM_NAME}' not found in {porter_yaml_path}")

    return parameter["default"]


def _get_schema_default(workspace_dir: Path) -> bool:
    schema_path = workspace_dir / "template_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for branch in schema["allOf"]:
        properties = branch.get("else", {}).get("properties", {})
        if PARAM_NAME in properties:
            return properties[PARAM_NAME]["default"]

    raise AssertionError(f"Property '{PARAM_NAME}' not found in {schema_path}")


class WorkspaceTemplateDefaultsTests(unittest.TestCase):
    def test_create_aad_groups_defaults_are_consistent_and_true(self):
        for bundle in WORKSPACE_BUNDLES:
            workspace_dir = REPO_ROOT / "templates" / "workspaces" / bundle
            with self.subTest(bundle=bundle):
                porter_default = _get_porter_default(workspace_dir)
                schema_default = _get_schema_default(workspace_dir)

                self.assertIs(porter_default, True, f"{bundle}: porter.yaml default for '{PARAM_NAME}' must be true")
                self.assertIs(
                    schema_default, True, f"{bundle}: template_schema.json default for '{PARAM_NAME}' must be true"
                )


if __name__ == "__main__":
    unittest.main()
