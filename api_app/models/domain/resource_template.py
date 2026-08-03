from typing import Dict, Any, List, Optional, Union

from pydantic import ConfigDict, Field, model_serializer

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import ResourceType


def _strip_none_recursive(obj: Any) -> None:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if obj[key] is None:
                del obj[key]
            else:
                _strip_none_recursive(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            _strip_none_recursive(item)


class Property(AzureTREModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra="allow")  # extra preserves unknown JSON Schema keywords (e.g. $ref, oneOf, format)

    @model_serializer(mode='plain')
    def _serialize(self) -> dict:
        # Emit only explicitly-set fields plus extra keywords; strip None at all nesting levels
        if not hasattr(self, 'model_fields_set'):
            # Pydantic passed an uncoerced plain dict (e.g. via item-level assignment to properties)
            result = {k: v for k, v in self.items() if v is not None}
            _strip_none_recursive(result)
            return result
        data = {k: v for k, v in ((f, getattr(self, f)) for f in self.model_fields_set) if v is not None}
        if self.__pydantic_extra__:
            data.update({k: v for k, v in self.__pydantic_extra__.items() if v is not None})
        _strip_none_recursive(data)
        return data

    type: Optional[str] = Field(default=None, title="Property type")
    title: str = Field(default="", title="Property description")
    description: Optional[str] = Field(default=None, title="Property description")
    default: Any = Field(default=None, title="Default value for the property")
    enum: Optional[List[str]] = Field(default=None, title="Enum values")
    const: Optional[Any] = Field(default=None, title="Constant value")
    multipleOf: Optional[float] = Field(default=None, title="Multiple of")
    maximum: Optional[float] = Field(default=None, title="Maximum value")
    exclusiveMaximum: Optional[float] = Field(default=None, title="Exclusive maximum value")
    minimum: Optional[float] = Field(default=None, title="Minimum value")
    exclusiveMinimum: Optional[float] = Field(default=None, title="Exclusive minimum value")
    maxLength: Optional[int] = Field(default=None, title="Maximum length")
    minLength: Optional[int] = Field(default=None, title="Minimum length")
    pattern: Optional[str] = Field(default=None, title="Pattern")
    updateable: Optional[bool] = Field(default=None, title="Indicates that the field can be updated")
    sensitive: Optional[bool] = Field(default=None, title="Indicates that the field is a sensitive value")
    readOnly: Optional[bool] = Field(default=None, title="Indicates the field is read-only")
    items: Optional[dict] = None  # items can contain sub-properties
    properties: Optional[dict] = None


class CustomAction(AzureTREModel):
    name: Optional[str] = Field(default=None, title="Custom action name")
    description: str = Field(default="", title="Action description")


class PipelineStepProperty(AzureTREModel):
    name: str = Field(title="name", description="name of the property to update")
    type: str = Field(title="type", description="data type of the property to update")
    value: Optional[Union[dict, str]] = Field(default=None, title="value", description="value to use in substitution for the property to update")
    arraySubstitutionAction: Optional[str] = Field(default="", title="Array Substitution Action", description="How to treat existing values of this property in an array [overwrite | append | replace | remove]")
    arrayMatchField: Optional[str] = Field(default="", title="Array match field", description="Name of the field to use for finding an item in an array - to replace/remove it")


class PipelineStep(AzureTREModel):
    stepId: Optional[str] = Field(default=None, title="stepId", description="Unique id identifying the step")
    stepTitle: Optional[str] = Field(default=None, title="stepTitle", description="Human readable title of what the step is for")
    resourceTemplateName: Optional[str] = Field(default=None, title="resourceTemplateName", description="Name of the template for the resource under change")
    resourceType: Optional[ResourceType] = Field(default=None, title="resourceType", description="Type of resource under change")
    resourceAction: Optional[str] = Field(default=None, title="resourceAction", description="Action - install / upgrade / uninstall etc")
    properties: Optional[List[PipelineStepProperty]] = None


class Pipeline(AzureTREModel):
    install: Optional[List[PipelineStep]] = None
    upgrade: Optional[List[PipelineStep]] = None
    uninstall: Optional[List[PipelineStep]] = None


class ResourceTemplate(AzureTREModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, validate_assignment=True)

    @model_serializer(mode='wrap')
    def _serialize(self, handler: Any, info: Any) -> dict:
        data = handler(self)
        _strip_none_recursive(data)  # covers allOf and other plain-dict fields missed by exclude_none
        return data

    id: str
    name: str = Field(title="Unique template name")
    title: str = Field(default="", title="Template title or friendly name")
    description: str = Field(default="", title="Template description")
    version: str = Field(title="Template version")
    resourceType: ResourceType = Field(title="Type of resource this template is for (workspace/service)")
    current: bool = Field(title="Is this the current version of this template")
    type: str = "object"
    required: List[str] = Field(title="List of properties which must be provided")
    authorizedRoles: Optional[List[str]] = Field(default_factory=list, title="If not empty, the user is required to have one of these roles to install the template")
    properties: Dict[str, Property] = Field(title="Template properties")
    allOf: Optional[List[dict]] = Field(default=None, title="All Of", description="Used for conditionally showing and validating fields")
    actions: List[CustomAction] = Field(default_factory=list, title="Template actions")
    customActions: List[CustomAction] = Field(default_factory=list, title="Template custom actions")
    pipeline: Optional[Pipeline] = Field(default=None, title="Template pipeline to define updates to other resources")
    uiSchema: Optional[dict] = Field(default_factory=dict, title="Dict containing a uiSchema object, if any")

    # setting this to false means if extra, unexpected fields are supplied, the request is invalidated
    unevaluatedProperties: bool = Field(default=False, title="Prevent unspecified properties being applied")
