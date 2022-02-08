from pydantic import Field

from models.domain.request_action import RequestAction
from models.domain.resource import Resource, ResourceType


class WorkspaceService(Resource):
    """
    Workspace service request
    """
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    resourceType = ResourceType.WorkspaceService

    def get_resource_request_message_payload(self, operation_id: str, action: RequestAction) -> dict:
        message_content = super().get_resource_request_message_payload(operation_id, action)
        message_content["workspaceId"] = self.workspaceId
        return message_content
