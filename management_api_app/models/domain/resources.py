from enum import Enum
from typing import List, Type
from uuid import UUID
from models.domain.azuretremodel import AzureTREModel


class ResourceType(Enum):
    Workspace = 1
    Service = 2


class Status(Enum):
    NotDeployed = 1
    Deploying = 2
    Deployed = 3
    Tearing = 4
    Down = 5


class Property:
    title: str
    description: str
    propertyType: Type
    default: Type
    required: bool
    mutable: bool
    value: Type


class Resource(AzureTREModel):
    id: UUID
    parentId: UUID
    version: str
    description: str
    resourceType: ResourceType
    status: Status
    properties: List[Property]
    etag: str
