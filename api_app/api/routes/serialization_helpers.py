"""
Utility functions for handling Pydantic v2 serialization compatibility.
This module provides helper functions to ensure proper serialization of Pydantic models
during the migration from Pydantic v1 to v2.
"""

from typing import Any, Dict, Union


def ensure_serialized_dict(obj: Any) -> Union[Dict, Any]:
    """
    Ensures that a Pydantic model or object is properly serialized to a dictionary.

    This function handles the transition from Pydantic v1 to v2 by checking for
    the presence of model_dump() method (v2) and falling back to the object itself
    if the method is not available.

    Args:
        obj: The object to serialize (could be a Pydantic model or already a dict)

    Returns:
        A dictionary representation of the object, or the object itself if already serialized
    """
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    return obj


def ensure_properties_serialized(resource_dict: Dict[str, Any], original_resource: Any) -> None:
    """
    Ensures that the 'properties' field in a resource dictionary is properly serialized.

    This function handles cases where the properties field might still be a Pydantic model
    after the main model has been serialized to a dictionary.

    Args:
        resource_dict: The dictionary representation of the resource
        original_resource: The original resource object (for fallback access)
    """
    if 'properties' not in resource_dict:
        return

    properties = resource_dict['properties']

    # Check if properties is still a Pydantic model and needs serialization
    if hasattr(properties, 'model_dump'):
        resource_dict['properties'] = properties.model_dump()
    elif hasattr(original_resource, 'properties') and hasattr(original_resource.properties, 'model_dump'):
        # Fallback: access properties from original object if dict serialization didn't work properly
        resource_dict['properties'] = original_resource.properties.model_dump()


def prepare_resource_for_response(resource: Any) -> Dict[str, Any]:
    """
    Prepares a resource object for API response by ensuring proper serialization.

    This function combines the serialization of the main resource and its nested
    properties field to ensure everything is properly converted to dictionaries.

    Args:
        resource: The resource object to prepare

    Returns:
        A dictionary representation of the resource with all nested objects serialized
    """
    resource_dict = ensure_serialized_dict(resource)
    ensure_properties_serialized(resource_dict, resource)
    return resource_dict
