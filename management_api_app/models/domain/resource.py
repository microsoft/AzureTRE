from enum import Enum
from uuid import UUID
from models.domain.azuretremodel import AzureTREModel


class ResourceType(str, Enum):
    Workspace = "workspace"
    Service = "service"


class Resource(AzureTREModel):
    id: UUID
    description: str
    resourceType: ResourceType
