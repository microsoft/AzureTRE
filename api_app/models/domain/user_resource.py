from pydantic import Field

from models.domain.request_action import RequestAction
from models.domain.resource import Resource, ResourceType


class UserResource(Resource):
    """
    Workspace service request
    """
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    ownerId: str = Field("", title="Owner of the user resource")
    parentWorkspaceServiceId: str = Field("", title="Parent Workspace Service ID", description="Service target Workspace Service id")
    azureStatus: dict = Field({}, title="Azure Status", description="Azure status, varies per user resoruce")
    resourceType = ResourceType.UserResource

    def get_resource_request_message_payload(self, operation_id: str, action: RequestAction) -> dict:
        message_content = super().get_resource_request_message_payload(operation_id, action)
        message_content["workspaceId"] = self.workspaceId
        message_content["ownerId"] = self.ownerId
        message_content["parentWorkspaceServiceId"] = self.parentWorkspaceServiceId
        return message_content
