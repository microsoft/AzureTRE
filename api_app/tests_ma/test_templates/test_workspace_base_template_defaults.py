import json
import re
from pathlib import Path

import yaml

# The workspace base template's `create_aad_groups` parameter default must stay
# `true` and stay identical in both porter.yaml and template_schema.json.
#
# See https://github.com/microsoft/AzureTRE/issues/5050 - RJSF materializes the
# JSON schema default whenever an older workspace has no stored value for an
# updateable property. If the schema default diverges from the Porter default
# (or from `true`), an unrelated workspace edit can silently submit `false` and
# Terraform will destroy the workspace's AAD role groups and app-role
# assignments.
REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_WORKSPACE_DIR = REPO_ROOT / "templates" / "workspaces" / "base"
PARAM_NAME = "create_aad_groups"


def _get_porter_default() -> bool:
    porter_yaml_path = BASE_WORKSPACE_DIR / "porter.yaml"
    with open(porter_yaml_path, "r") as f:
        # porter.yaml uses CNAB templating expressions (e.g. ${ bundle... })
        # which the default PyYAML loader chokes on outside of string values,
        # so drop any leading document separator and rely on default
        # scalar handling for the rest of the file.
        content = re.sub(r"^---\n", "", f.read())
        porter = yaml.safe_load(content)

    for parameter in porter["parameters"]:
        if parameter["name"] == PARAM_NAME:
            return parameter["default"]

    raise AssertionError(f"Parameter '{PARAM_NAME}' not found in {porter_yaml_path}")


def _get_schema_default() -> bool:
    schema_path = BASE_WORKSPACE_DIR / "template_schema.json"
    with open(schema_path, "r") as f:
        content = f.read()

    schema = json.loads(content)
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
