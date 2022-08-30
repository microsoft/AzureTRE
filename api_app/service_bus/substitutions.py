from typing import Union
from models.domain.resource_template import PipelineStep
from models.domain.resource import Resource


def substitute_properties(template_step: PipelineStep, primary_resource: Resource, resource_to_update: Resource) -> dict:
    properties = {}
    primary_resource_dict = primary_resource.dict()

    for prop in template_step.properties:
        val = prop.value
        if isinstance(prop.value, dict):
            val = recurse_object(prop.value, primary_resource_dict)

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
            val = substitute_value(val, primary_resource_dict)
            properties[prop.name] = val

    return properties


def find_item_index(array: list, arrayMatchField: str, val: dict) -> int:
    for i in range(0, len(array)):
        if array[i][arrayMatchField] == val[arrayMatchField]:
            return i
    return -1


def recurse_object(obj: dict, primary_resource_dict: dict) -> dict:
    for prop in obj:
        if isinstance(obj[prop], list):
            for i in range(0, len(obj[prop])):
                if isinstance(obj[prop][i], list) or isinstance(obj[prop][i], dict):
                    obj[prop][i] = recurse_object(obj[prop][i], primary_resource_dict)
                else:
                    obj[prop][i] = substitute_value(obj[prop][i], primary_resource_dict)
        if isinstance(obj[prop], dict):
            obj[prop] = recurse_object(obj[prop], primary_resource_dict)
        else:
            obj[prop] = substitute_value(obj[prop], primary_resource_dict)

    return obj


def substitute_value(val: str, primary_resource_dict: dict) -> Union[dict, list, str]:
    if "{{" not in val:
        return val

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

    for t in tokens:
        # t = "resource.properties.prop_1"
        p = t.split(".")
        if p[0] == "resource":
            prop_to_get = primary_resource_dict
            for i in range(1, len(p)):
                prop_to_get = prop_to_get[p[i]]

            # if the value to inject is actually an object / list - just return it, else replace the value in the string
            if isinstance(prop_to_get, dict) or isinstance(prop_to_get, list):
                return prop_to_get
            else:
                val = val.replace("{{" + t + "}}", str(prop_to_get))

    return val
