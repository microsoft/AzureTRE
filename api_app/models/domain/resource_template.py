from typing import Dict, Any, List, Optional

from pydantic import Field

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import ResourceType


class Property(AzureTREModel):
    type: str = Field(title="Property type")
    title: str = Field("", title="Property description")
    description: str = Field("", title="Property description")
    default: Any = Field(None, title="Default value for the property")
    enum: Optional[List[str]] = Field(None, title="Enum values")
    const: Optional[Any] = Field(None, title="Constant value")
    multipleOf: Optional[float] = Field(None, title="Multiple of")
    maximum: Optional[float] = Field(None, title="Maximum value")
    exclusiveMaximum: Optional[float] = Field(None, title="Exclusive maximum value")
    minimum: Optional[float] = Field(None, title="Minimum value")
    exclusiveMinimum: Optional[float] = Field(None, title="Exclusive minimum value")
    maxLength: Optional[int] = Field(None, title="Maximum length")
    minLength: Optional[int] = Field(None, title="Minimum length")
    pattern: Optional[str] = Field(None, title="Pattern")
    updateable: Optional[bool] = Field(None, title="Indicates that the field can be updated")
    readOnly: Optional[bool] = Field(None, title="Indicates the field is read-only")


class CustomAction(AzureTREModel):
    name: str = Field(None, title="Custom action name")
    description: str = Field("", title="Action description")


class ResourceTemplate(AzureTREModel):
    id: str
    name: str = Field(title="Unique template name")
    title: str = Field("", title="Template title or friendly name")
    description: str = Field(title="Template description")
    version: str = Field(title="Template version")
    resourceType: ResourceType = Field(title="Type of resource this template is for (workspace/service)")
    current: bool = Field(title="Is this the current version of this template")
    type: str = "object"
    required: List[str] = Field(title="List of properties which must be provided")
    properties: Dict[str, Property] = Field(title="Template properties")
    actions: List[CustomAction] = Field(default=[], title="Template actions")
    customActions: List[CustomAction] = Field(default=[], title="Template custom actions")

    # setting this to false means if extra, unexpected fields are supplied, the request is invalidated
    additionalProperties: bool = Field(default=False, title="Prevent unspecified properties being applied")
