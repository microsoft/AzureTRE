import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_WORKSPACE_DIR = REPO_ROOT / "templates" / "workspaces" / "base"
PARAM_NAME = "create_aad_groups"


def _get_porter_default() -> bool:
    porter_yaml_path = BASE_WORKSPACE_DIR / "porter.yaml"
    porter = yaml.safe_load(porter_yaml_path.read_text(encoding="utf-8"))
    parameter = next(
        (
            parameter
            for parameter in porter["parameters"]
            if parameter["name"] == PARAM_NAME
        ),
        None,
    )
    if parameter is None:
        raise AssertionError(f"Parameter '{PARAM_NAME}' not found in {porter_yaml_path}")

    return parameter["default"]


def _get_schema_default() -> bool:
    schema_path = BASE_WORKSPACE_DIR / "template_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for branch in schema["allOf"]:
        properties = branch.get("else", {}).get("properties", {})
        if PARAM_NAME in properties:
            return properties[PARAM_NAME]["default"]

    raise AssertionError(f"Property '{PARAM_NAME}' not found in {schema_path}")


def test_workspace_base_create_aad_groups_defaults_are_consistent_and_true():
    porter_default = _get_porter_default()
    schema_default = _get_schema_default()

    assert porter_default is True, (
        f"porter.yaml default for '{PARAM_NAME}' must be true, got {porter_default}"
    )
    assert schema_default is True, (
        f"template_schema.json default for '{PARAM_NAME}' must be true, got {schema_default}"
    )
    assert porter_default == schema_default, (
        f"porter.yaml and template_schema.json defaults for '{PARAM_NAME}' must match "
        f"(porter={porter_default}, schema={schema_default})"
    )


if __name__ == "__main__":
    test_workspace_base_create_aad_groups_defaults_are_consistent_and_true()
