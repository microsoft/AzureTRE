from enum import Enum
from pydantic import Field

from models.domain.azuretremodel import AzureTREModel
from models.domain.request_action import RequestAction
from resources import strings


class ResourceType(str, Enum):
    """
    Type of resource to deploy
    """
    Workspace = strings.RESOURCE_TYPE_WORKSPACE
    WorkspaceService = strings.RESOURCE_TYPE_WORKSPACE_SERVICE
    UserResource = strings.USER_RESOURCE


class Resource(AzureTREModel):
    """
    Resource request
    """
    id: str = Field(title="Id", description="GUID identifying the resource request")
    templateName: str = Field(title="Resource template name", description="The resource template (bundle) to deploy")
    templateVersion: str = Field(title="Resource template version", description="The version of the resource template (bundle) to deploy")
    properties: dict = Field({}, title="Resource template parameters", description="Parameters for the deployment")
    isActive: bool = Field(True, title="Is Active", description="Is the resource active? Will be False when deleted.")
    resourceType: ResourceType
    resourcePath: str = ""

    def is_enabled(self) -> bool:
        if "enabled" not in self.properties:
            return True     # default behavior is enabled = True
        return self.properties["enabled"] is True

    def get_resource_request_message_payload(self, operation_id: str, action: RequestAction) -> dict:
        return {
            "operationId": operation_id,
            "action": action,
            "id": self.id,
            "name": self.templateName,
            "version": self.templateVersion,
            "parameters": self.properties
        }


class Output(AzureTREModel):
    Name: str = Field(title="", description="")
    Value: str = Field(title="", description="")
