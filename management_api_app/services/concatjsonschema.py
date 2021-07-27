import json
from pathlib import Path


def system_properties_block():
    return {
        "tre_id": {
            "type": "string"
        },
        "workspace_id": {
            "type": "string"
        },
        "azure_location": {
            "type": "string"
        }
    }


def merge_required(tuples):
    required = [tup[0] for tup in tuples]
    flattened = [val for sublist in required for val in sublist]
    return flattened


def merge_properties(tuples):
    properties = {}
    for tup in tuples:
        properties.update(tup[1])
    return properties


def read_schema(schema_file):
    workspace_schema_def = Path(__file__).parent / ".." / "schemas" / schema_file
    with open(workspace_schema_def) as schema_f:
        schema = json.load(schema_f)
        return (schema["required"], schema["properties"])


def load_workspace_schema_def():
    return read_schema("workspace.json")


def load_azuread_schema_def():
    return read_schema("azuread.json")


def enrich_schema_defs(combine_with, print_result=None):
    """Adds to the provided template all UI and system properties

    Args:
        combine_with ([Dict]): [Template to which UI and system properties are added].
    Returns:
        [Dict]: [Enriched template with all required and system properties added]
    """
    combine_with_dict = combine_with.dict()
    workspace_tuple = load_workspace_schema_def()
    schema_tuple = load_azuread_schema_def()
    given_template_tuple = (combine_with_dict["required"], combine_with_dict["properties"])
    basic_blocks = [workspace_tuple, schema_tuple, given_template_tuple]
    combine_with_dict["required"] = merge_required(basic_blocks)
    combine_with_dict["properties"] = merge_properties(basic_blocks)
    combine_with_dict["system_properties"] = system_properties_block()
    return combine_with_dict
