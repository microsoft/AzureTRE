from enum import Enum
from pydantic import Field

from models.domain.azuretremodel import AzureTREModel
from models.domain.request_action import RequestAction
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
    WorkspaceService = strings.RESOURCE_TYPE_WORKSPACE_SERVICE
    UserResource = strings.USER_RESOURCE


class Deployment(AzureTREModel):
    status: Status = Field(Status.NotDeployed, title="Deployment status")
    message: str = Field("", title="Additional deployment status information")


class Resource(AzureTREModel):
    """
    Resource request
    """
    id: str = Field(title="Id", description="GUID identifying the resource request")
    resourceTemplateName: str = Field(title="Resource template name", description="The resource template (bundle) to deploy")
    resourceTemplateVersion: str = Field(title="Resource template version", description="The version of the resource template (bundle) to deploy")
    resourceTemplateParameters: dict = Field({}, title="Resource template parameters", description="Parameters for the deployment")
    deployment: Deployment = Field(Deployment(status=Status.NotDeployed, message=""), title="Deployment", description="Fields related to deployment of this resource")
    resourceType: ResourceType

    def is_enabled(self) -> bool:
        if "enabled" not in self.resourceTemplateParameters:
            return True     # default behavior is enabled = True
        return self.resourceTemplateParameters["enabled"] is True

    def get_resource_request_message_payload(self, action: RequestAction) -> dict:
        return {
            "action": action,
            "id": self.id,
            "name": self.resourceTemplateName,
            "version": self.resourceTemplateVersion,
            "parameters": self.resourceTemplateParameters
        }
