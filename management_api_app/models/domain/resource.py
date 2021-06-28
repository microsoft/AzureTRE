from enum import Enum
from pydantic import Field

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
    Failed = strings.RESOURCE_STATUS_FAILED


class ResourceType(str, Enum):
    """
    Type of resource to deploy
    """
    Workspace = strings.RESOURCE_TYPE_WORKSPACE
    Service = strings.RESOURCE_TYPE_SERVICE


class Deployment(AzureTREModel):
    status: Status = Field(Status.NotDeployed, title="Deployment status")
    message: str = Field("", title="Additional deployment status information")


class Resource(AzureTREModel):
    """
    Resource request
    """
    id: str = Field(title="Id", description="GUID identifying the resource request")
    displayName: str = Field("", title="Display name", description="Friendly name for the workspace/service")
    description: str = Field("", title="Description", description="Short description of how the workspace/service is used")
    resourceTemplateName: str = Field(title="Resource template name", description="The resource template (bundle) to deploy")
    resourceTemplateVersion: str = Field(title="Resource template version", description="The version of the resource template (bundle) to deploy")
    resourceTemplateParameters: dict = Field({}, title="Resource template parameters", description="Parameters for the deployment")
    deployment: Deployment = Field(Deployment(status=Status.NotDeployed, message=""), title="Deployment", description="Fields related to deployment of this resource")
    isDeleted: bool = Field(False, title="Is deleted", description="Marks the resource request as deleted (NOTE: this is not the deployment status)")
