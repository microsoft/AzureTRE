from typing import List, Optional, Any

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import ResourceType


class Parameter(AzureTREModel):
    name: str
    type: str
    default: Any
    applyTo: str = "All Actions"
    description: Optional[str]
    required: bool = False


class ResourceTemplate(AzureTREModel):
    name: str
    description: str
    version: str
    parameters: List[Parameter]
    resourceType: ResourceType
    current: bool
