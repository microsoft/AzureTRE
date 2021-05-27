from enum import Enum
from uuid import UUID
from models.domain.azuretremodel import AzureTREModel
from resources import strings


class Status(str, Enum):
    NotDeployed = strings.RESOURCE_STATUS_NOT_DEPLOYED
    Deploying = strings.RESOURCE_STATUS_DEPLOYING
    Deployed = strings.RESOURCE_STATUS_DEPLOYED
    Deleting = strings.RESOURCE_STATUS_DELETING
    Deleted = strings.RESOURCE_STATUS_DELETED


class ResourceType(str, Enum):
    Workspace = strings.RESOURCE_TYPE_WORKSPACE
    Service = strings.RESOURCE_TYPE_SERVICE


class Resource(AzureTREModel):
    id: UUID
    description: str
    resourceType: ResourceType
    status: Status
