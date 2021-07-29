from typing import Dict, Any, List

from pydantic import Field

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import ResourceType


class Property(AzureTREModel):
    type: str = Field(title="Property type")
    title: str = Field("", title="Property description")
    description: str = Field("", title="Property description")
    default: Any = Field(None, title="Default value for the property")


class ResourceTemplate(AzureTREModel):
    id: str
    name: str = Field(title="Unique template name")
    description: str = Field(title="Template description")
    version: str = Field(title="Template version")
    resourceType: ResourceType = Field(title="Type of resource this template is for (workspace/service)")
    current: bool = Field(title="Is this the current version of this template")
    type: str = "object"
    required: List[str] = Field(title="List of properties which must be provided")
    properties: Dict[str, Property] = Field(title="Template properties")
