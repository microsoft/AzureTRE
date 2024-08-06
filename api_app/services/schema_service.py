import json
from pathlib import Path
from typing import List, Dict, Tuple


def get_system_properties(id_field: str = "workspace_id"):
    return {
        "tre_id": {
            "type": "string"
        },
        id_field: {
            "type": "string"
        },
        "azure_location": {
            "type": "string"
        }
    }


def merge_required(all_required):
    required_lists = [prop_list for prop_list in all_required]
    flattened_required = [prop for prop_list in required_lists for prop in prop_list]
    return list(set(flattened_required))


def merge_properties(all_properties: List[Dict]) -> Dict:
    properties = {}
    for prop in all_properties:
        properties.update(prop)
    return properties


def read_schema(schema_file: str) -> Tuple[List[str], Dict]:
    workspace_schema_def = Path(__file__).parent / ".." / "schemas" / schema_file
    with open(workspace_schema_def) as schema_f:
        schema = json.load(schema_f)
        return schema["required"], schema["properties"]


def enrich_template(original_template, extra_properties, is_update: bool = False, is_workspace_scope: bool = True) -> dict:
    template = original_template.dict(exclude_none=True)

    all_required = [definition[0] for definition in extra_properties] + [template["required"]]
    all_properties = [definition[1] for definition in extra_properties] + [template["properties"]]

    template["required"] = merge_required(all_required)
    template["properties"] = merge_properties(all_properties)

    # if this is an update, mark the non-updateable properties as readOnly
    # this will help the UI render fields appropriately and know what it can send in a PATCH
    if is_update:
        for prop in template["properties"].values():
            if not prop.get("updateable", False):
                prop["readOnly"] = True

        if "allOf" in template:
            for conditional_property in template["allOf"]:
                for condition in ["then", "else"]:
                    if condition in conditional_property and "properties" in conditional_property[condition]:
                        for prop in conditional_property[condition]["properties"].values():
                            if not prop.get("updateable", False):
                                prop["readOnly"] = True

    # if there is an 'allOf' property which is empty, the validator fails - so remove the key
    if "allOf" in template and template["allOf"] is None:
        template.pop("allOf")

    if is_workspace_scope:
        id_field = "workspace_id"
    else:
        id_field = "shared_service_id"
    template["system_properties"] = get_system_properties(id_field)
    return template


def enrich_workspace_template(template, is_update: bool = False) -> dict:
    """Adds to the provided template all UI and system properties
    Args:
        template: [Template to which UI and system properties are added].
        is_update: [Indicates that the schema is to be used in an update (PATCH) operation]
    Returns:
        [Dict]: [Enriched template with all required and system properties added]
    """
    workspace_default_properties = read_schema('workspace.json')
    azure_ad_properties = read_schema('azuread.json')
    return enrich_template(template, [workspace_default_properties, azure_ad_properties], is_update=is_update)


def enrich_workspace_service_template(template, is_update: bool = False) -> dict:
    """Adds to the provided template all UI and system properties
    Args:
        template: [Template to which UI and system properties are added].
        is_update: [Indicates that the schema is to be used in an update (PATCH) operation]
    Returns:
        [Dict]: [Enriched template with all required and system properties added]
    """
    workspace_service_default_properties = read_schema('workspace_service.json')
    return enrich_template(template, [workspace_service_default_properties], is_update=is_update)


def enrich_shared_service_template(template, is_update: bool = False) -> dict:
    """Adds to the provided template all UI and system properties
    Args:
        template: [Template to which UI and system properties are added].
    Returns:
        [Dict]: [Enriched template with all required and system properties added]
    """
    shared_service_default_properties = read_schema('shared_service.json')
    return enrich_template(template, [shared_service_default_properties], is_update=is_update, is_workspace_scope=False)


def enrich_user_resource_template(template, is_update: bool = False):
    """Adds to the provided template all UI and system properties
    Args:
        template: [Template to which UI and system properties are added].
        is_update: [Indicates that the schema is to be used in an update (PATCH) operation]
    Returns:
        [Dict]: [Enriched template with all required and system properties added]
    """
    user_resource_default_properties = read_schema('user_resource.json')
    return enrich_template(template, [user_resource_default_properties], is_update=is_update)
