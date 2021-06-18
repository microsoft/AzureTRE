from typing import List, Any

from pydantic import Field

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import ResourceType


class Parameter(AzureTREModel):
    name: str = Field(title="Parameter name")
    type: str = Field(title="Parameter type")
    default: Any = Field(None, title="Default value for the parameter")
    applyTo: str = Field("All Actions", title="The actions that the parameter applies to e.g. install, delete etc")
    description: str = Field("", title="Parameter description")
    required: bool = Field(False, title="Is the parameter required")


class ResourceTemplate(AzureTREModel):
    id: str
    name: str = Field(title="Unique template name")
    description: str = Field(title="Template description")
    version: str = Field(title="Template version")
    parameters: List[Parameter] = Field(title="Template parameters")
    resourceType: ResourceType = Field(title="Type of resource this template is for (workspace/service)")
    current: bool = Field(title="Is this the current version of this template")
