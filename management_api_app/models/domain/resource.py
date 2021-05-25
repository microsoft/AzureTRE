from enum import Enum
from uuid import UUID
from models.domain.azuretremodel import AzureTREModel


class ResourceType(Enum):
    Workspace = 0
    Service = 1


class Resource(AzureTREModel):
    id: UUID
    description: str
    resourceType: ResourceType
