import json
from pathlib import Path
from typing import List, Dict, Tuple
from models.domain.resource_template import Property


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


def merge_properties(all_properties: List[Dict[str, Property]]) -> Dict[str, Property]:
    """Merge properties from multiple sources containing Property objects."""
    merged = {}
    for prop_dict in all_properties:
        merged.update(prop_dict)
    return merged


def read_schema(schema_file: str) -> Tuple[List[str], Dict[str, Property]]:
    workspace_schema_def = Path(__file__).parent / ".." / "schemas" / schema_file
    with open(workspace_schema_def) as schema_f:
        schema = json.load(schema_f)
        properties = {}
        for key, prop_dict in schema["properties"].items():
            properties[key] = Property(**prop_dict)
        return schema["required"], properties


def enrich_template(original_template, extra_properties, is_update: bool = False, is_workspace_scope: bool = True) -> dict:
    if hasattr(original_template, 'model_dump'):
        template = original_template.model_dump(exclude_none=True)
        template_properties = original_template.properties
    else:
        template = original_template.copy()
        template_properties = {}
        if "properties" in template:
            for k, v in template["properties"].items():
                template_properties[k] = Property(**v) if isinstance(v, dict) else v

    # Extract required lists and property dicts from extra_properties
    all_required = [definition[0] for definition in extra_properties] + [template["required"]]
    all_property_dicts = [definition[1] for definition in extra_properties] + [template_properties]

    template["required"] = merge_required(all_required)
    merged_properties = merge_properties(all_property_dicts)

    if is_update:
        for prop in merged_properties.values():
            if not getattr(prop, "updateable", False):
                prop.readOnly = True

        if "allOf" in template:
            for conditional_property in template["allOf"]:
                for condition in ["then", "else"]:
                    if condition in conditional_property and "properties" in conditional_property[condition]:
                        for prop_name, prop_data in conditional_property[condition]["properties"].items():
                            prop_obj = Property(**prop_data) if isinstance(prop_data, dict) else prop_data
                            if not getattr(prop_obj, "updateable", False):
                                prop_obj.readOnly = True
                            conditional_property[condition]["properties"][prop_name] = prop_obj.model_dump(exclude_defaults=True, exclude_none=True)

    # Convert Property objects to dictionaries for the final result
    template["properties"] = {
        k: v.model_dump(exclude_defaults=True, exclude_none=True) if hasattr(v, 'model_dump') else v
        for k, v in merged_properties.items()
    }

    # Clean up empty allOf
    if "allOf" in template and template["allOf"] is None:
        template.pop("allOf")

    # Add system properties
    id_field = "workspace_id" if is_workspace_scope else "shared_service_id"
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
