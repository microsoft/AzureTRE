from enum import Enum
from pydantic import Field
from typing import List, Dict

from models.domain.azuretremodel import AzureTREModel
from resources import strings


class Status(str, Enum):
    """
    Deployment status
    """
    NotDeployed = strings.RESOURCE_STATUS_NOT_DEPLOYED
    Deploying = strings.RESOURCE_STATUS_DEPLOYING
    Deployed = strings.RESOURCE_STATUS_DEPLOYED
    Deleting = strings.RESOURCE_STATUS_DELETING
    Deleted = strings.RESOURCE_STATUS_DELETED


class ResourceType(str, Enum):
    """
    Type of resource to deploy
    """
    Workspace = strings.RESOURCE_TYPE_WORKSPACE
    Service = strings.RESOURCE_TYPE_SERVICE


class ResourceSpec(AzureTREModel):
    name: str
    version: str
    id: str
    latest: str
    fields: List[Dict]


class Resource(AzureTREModel):
    """
    Resource request
    """
    id: str = Field(title="Id", description="GUID identifying the resource request")
    displayName: str = Field("", title="Display name", description="Friendly name for the workspace/service")
    description: str = Field("", title="Description", description="Short description of how the workspace/service is used")
    resourceSpecName: str = Field(title="Resource specification type", description="The resource specification (bundle) to deploy")
    resourceSpecVersion: str = Field(title="Resource specification version", description="The version of the resource spec (bundle) to deploy")
    resourceSpecParameters: dict = Field({}, title="Resource specification parameters", description="Parameters for the deployment")
    status: Status = Field(Status.NotDeployed, title="Deployment status")
    isDeleted: bool = Field(False, title="Is deleted", description="Marks the resource request as deleted (NOTE: this is not the deployment status)")
