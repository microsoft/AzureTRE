import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_WORKSPACE_DIR = REPO_ROOT / "templates" / "workspaces" / "base"
PARAM_NAME = "create_aad_groups"


def _get_porter_default() -> bool:
    porter_yaml_path = BASE_WORKSPACE_DIR / "porter.yaml"
    content = porter_yaml_path.read_text()
    match = re.search(
        rf"- name: {PARAM_NAME}\s+type: boolean\s+default: (true|false)",
        content,
    )
    if match is None:
        raise AssertionError(f"Parameter '{PARAM_NAME}' not found in {porter_yaml_path}")

    return match.group(1) == "true"


def _get_schema_default() -> bool:
    schema_path = BASE_WORKSPACE_DIR / "template_schema.json"
    schema = json.loads(schema_path.read_text())
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
