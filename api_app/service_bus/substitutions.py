from typing import Union
from resources import strings
from models.domain.resource_template import PipelineStep
from models.domain.resource import Resource


def substitute_properties(template_step: PipelineStep, primary_resource: Resource, primary_parent_workspace: Resource, primary_parent_workspace_svc: Resource, resource_to_update: Resource) -> dict:
    properties = {}
    parent_ws_dict = {}
    parent_ws_svc_dict = {}
    primary_resource_dict = primary_resource.dict()
    if primary_parent_workspace is not None:
        parent_ws_dict = primary_parent_workspace.dict()
    if primary_parent_workspace_svc is not None:
        parent_ws_svc_dict = primary_parent_workspace_svc.dict()

    if template_step is None or template_step.properties is None:
        return properties

    for prop in template_step.properties:
        val = prop.value
        if isinstance(prop.value, dict):
            val = recurse_object(prop.value, primary_resource_dict, parent_ws_dict, parent_ws_svc_dict)

            if prop.type == 'array':
                if prop.name in resource_to_update.properties:
                    existing_arr = resource_to_update.properties[prop.name]
                else:
                    existing_arr = []

                if prop.arraySubstitutionAction == 'overwrite':
                    existing_arr = [val]

                if prop.arraySubstitutionAction == 'append':
                    existing_arr.append(val)

                if prop.arraySubstitutionAction == 'remove':
                    item_index = find_item_index(existing_arr, prop.arrayMatchField, val)
                    if item_index > -1:
                        del existing_arr[item_index]

                if prop.arraySubstitutionAction == 'replace':
                    item_index = find_item_index(existing_arr, prop.arrayMatchField, val)
                    if item_index > -1:
                        existing_arr[item_index] = val
                    else:
                        existing_arr.append(val)

                properties[prop.name] = existing_arr

            else:
                properties[prop.name] = val

        else:
            val = substitute_value(val, primary_resource_dict, parent_ws_dict, parent_ws_svc_dict)
            properties[prop.name] = val

    return properties


def find_item_index(array: list, arrayMatchField: str, val: dict) -> int:
    for i in range(0, len(array)):
        if array[i][arrayMatchField] == val[arrayMatchField]:
            return i
    return -1


def recurse_object(obj: dict, resource_dict: dict, parent_ws_dict: dict, parent_ws_svc_dict: dict) -> dict:
    for prop in obj:
        if isinstance(obj[prop], list):
            for i in range(0, len(obj[prop])):
                if isinstance(obj[prop][i], list) or isinstance(obj[prop][i], dict):
                    obj[prop][i] = recurse_object(obj[prop][i], resource_dict, parent_ws_dict, parent_ws_svc_dict)
                else:
                    obj[prop][i] = substitute_value(obj[prop][i], resource_dict, parent_ws_dict, parent_ws_svc_dict)
        if isinstance(obj[prop], dict):
            obj[prop] = recurse_object(obj[prop], resource_dict, parent_ws_dict, parent_ws_svc_dict)
        else:
            obj[prop] = substitute_value(obj[prop], resource_dict, parent_ws_dict, parent_ws_svc_dict)

    return obj


def substitute_value(val: str, primary_resource_dict: dict, primary_parent_ws_dict: dict, primary_parent_ws_svc_dict: dict) -> Union[dict, list, str]:
    if "{{" not in val:
        return val

    if primary_resource_dict is None:
        raise Exception("primary_resource_dict cannot be None")
    primary_resource_type = primary_resource_dict["resourceType"]

    val = val.replace("{{ ", "{{").replace(" }}", "}}")

    # if the value being substituted in is a simple type, we can return it in the string, to allow for concatenation
    # like "This was deployed by {{ resource.id }}"
    # else if the value being injected in is a dict/list - we shouldn't try to concatenate that, we'll return the true value and drop any surrounding text

    # extract the tokens to replace
    tokens = []
    parts = val.split("{{")
    for p in parts:
        if len(p) > 0 and "}}" in p:
            t = p[0:p.index("}}")]
            tokens.append(t)

    dict_to_use = None
    for t in tokens:
        # t = "{resource[.parent][.parent].properties.prop_1"
        path_tokens = t.split(".")

        # decide on which dictionary to use (parents support)
        # how many parents levels do we have (0- current resource, 1-direct parent, 2-skip level parent, 3-invalid)
        hierarchy_level = 0
        for i in range(3, 0, -1):
            if len(path_tokens) > i:
                if path_tokens[i] == "parent":
                    hierarchy_level += 1

        # sanity
        if primary_resource_type == strings.USER_RESOURCE and hierarchy_level > 2:
            raise ValueError(f"parent.parent.parent is invalid for a resource of type '{strings.USER_RESOURCE}'")
        elif primary_resource_type == strings.RESOURCE_TYPE_WORKSPACE_SERVICE and hierarchy_level > 1:
            raise ValueError(f"parent.parent is invalid for a resource of type '{strings.RESOURCE_TYPE_WORKSPACE_SERVICE}'")
        elif primary_resource_type == strings.RESOURCE_TYPE_WORKSPACE and hierarchy_level > 0:
            raise ValueError(f"parent is invalid for a resource of type '{strings.RESOURCE_TYPE_WORKSPACE}'")
        elif primary_resource_type == strings.RESOURCE_TYPE_SHARED_SERVICE and hierarchy_level > 0:
            raise ValueError(f"parent is invalid for a resource of type '{strings.RESOURCE_TYPE_SHARED_SERVICE}'")

        if hierarchy_level == 2:
            if primary_resource_type == strings.USER_RESOURCE:
                dict_to_use = primary_parent_ws_dict
                del path_tokens[2]
                del path_tokens[1]
        elif hierarchy_level == 1:
            if primary_resource_type == strings.USER_RESOURCE:
                dict_to_use = primary_parent_ws_svc_dict
            elif primary_resource_type == strings.RESOURCE_TYPE_WORKSPACE_SERVICE:
                dict_to_use = primary_parent_ws_dict
            del path_tokens[1]
        else:
            dict_to_use = primary_resource_dict

        prop_to_get = dict_to_use
        for i in range(1, len(path_tokens)):
            # instead of failing, if the value is not found, return empty string. Used for backward compatability
            if path_tokens[i] not in prop_to_get:
                return ""
            prop_to_get = prop_to_get[path_tokens[i]]

        # if the value to inject is actually an object / list - just return it, else replace the value in the string
        if isinstance(prop_to_get, dict) or isinstance(prop_to_get, list):
            return prop_to_get
        else:
            val = val.replace("{{" + t + "}}", str(prop_to_get))

    return val
