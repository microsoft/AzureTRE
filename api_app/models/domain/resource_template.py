from typing import Dict, Any, List, Optional, Union

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
    sensitive: Optional[bool] = Field(None, title="Indicates that the field is a sensitive value")
    readOnly: Optional[bool] = Field(None, title="Indicates the field is read-only")
    items: Optional[dict] = None  # items can contain sub-properties
    properties: Optional[dict] = None


class CustomAction(AzureTREModel):
    name: str = Field(None, title="Custom action name")
    description: str = Field("", title="Action description")


class PipelineStepProperty(AzureTREModel):
    name: str = Field(title="name", description="name of the property to update")
    type: str = Field(title="type", description="data type of the property to update")
    value: Union[dict, str] = Field(None, title="value", description="value to use in substitution for the property to update")
    arraySubstitutionAction: Optional[str] = Field("", title="Array Substitution Action", description="How to treat existing values of this property in an array [overwrite | append | replace | remove]")
    arrayMatchField: Optional[str] = Field("", title="Array match field", description="Name of the field to use for finding an item in an array - to replace/remove it")


class PipelineStep(AzureTREModel):
    stepId: Optional[str] = Field(title="stepId", description="Unique id identifying the step")
    stepTitle: Optional[str] = Field(title="stepTitle", description="Human readable title of what the step is for")
    resourceTemplateName: Optional[str] = Field(title="resourceTemplateName", description="Name of the template for the resource under change")
    resourceType: Optional[ResourceType] = Field(title="resourceType", description="Type of resource under change")
    resourceAction: Optional[str] = Field(title="resourceAction", description="Action - install / upgrade / uninstall etc")
    properties: Optional[List[PipelineStepProperty]]


class Pipeline(AzureTREModel):
    install: Optional[List[PipelineStep]]
    upgrade: Optional[List[PipelineStep]]
    uninstall: Optional[List[PipelineStep]]


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
    authorizedRoles: Optional[List[str]] = Field(default=[], title="If not empty, the user is required to have one of these roles to install the template")
    properties: Dict[str, Property] = Field(title="Template properties")
    allOf: Optional[List[dict]] = Field(default=None, title="All Of", description="Used for conditionally showing and validating fields")
    actions: List[CustomAction] = Field(default=[], title="Template actions")
    customActions: List[CustomAction] = Field(default=[], title="Template custom actions")
    pipeline: Optional[Pipeline] = Field(default=None, title="Template pipeline to define updates to other resources")
    uiSchema: Optional[dict] = Field(default={}, title="Dict containing a uiSchema object, if any")

    # setting this to false means if extra, unexpected fields are supplied, the request is invalidated
    unevaluatedProperties: bool = Field(default=False, title="Prevent unspecified properties being applied")
