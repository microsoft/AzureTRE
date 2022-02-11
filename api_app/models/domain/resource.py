from enum import Enum
from typing import List
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


class ResourceHistoryItem(AzureTREModel):
    """
    Resource History Item - to preserve history of resource properties
    """
    properties: dict = {}
    isEnabled: bool
    resourceVersion: int
    updatedWhen: float


class Resource(AzureTREModel):
    """
    Resource request
    """
    id: str = Field(title="Id", description="GUID identifying the resource request")
    templateName: str = Field(title="Resource template name", description="The resource template (bundle) to deploy")
    templateVersion: str = Field(title="Resource template version", description="The version of the resource template (bundle) to deploy")
    properties: dict = Field({}, title="Resource template parameters", description="Parameters for the deployment")
    isActive: bool = True  # When False, hides resource document from list views
    isEnabled: bool = True  # Must be set before a resource can be deleted
    resourceType: ResourceType
    etag: str = Field(title="_etag", description="eTag of the document", alias="_etag")
    resourcePath: str = ""
    resourceVersion: int = 0
    history: List[ResourceHistoryItem] = []

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
