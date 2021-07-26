import json
from pathlib import Path


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


def print_formatted_json(required, properties):
    for j in [required, properties]:
        json_formatted_str = json.dumps(j, indent=4)
        print(json_formatted_str)


def concat_schema_defs(combine_with=None, print_result=None):
    """Combines schema definitions of known blocks with optional schema

    Args:
        combine_with ([Tuple], optional): [Optional schema defs of a workspace]. Defaults to None.
    Returns:
        [Tuple]: [A tuple of merged required list and properties dictionary]
    """
    workspace_tuple = load_workspace_schema_def()
    schema_tuple = load_azuread_schema_def()
    basic_blocks = [workspace_tuple, schema_tuple]
    _ = basic_blocks if not combine_with else basic_blocks.append(combine_with)
    required = merge_required(basic_blocks)
    properties = merge_properties(basic_blocks)
    if print_result:
        print_formatted_json(required, properties)
    return (required, properties)


if __name__ == "__main__":
    concat_schema_defs(print_result=True)
