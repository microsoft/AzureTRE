from pydantic import Field
from models.domain.resource import Resource, ResourceType


class WorkspaceService(Resource):
    """
    Workspace service request
    """
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    resourceType = ResourceType.WorkspaceService

    def get_resource_request_message_payload(self) -> dict:
        message_content = super().get_resource_request_message_payload()
        message_content["workspaceId"] = self.workspaceId
        return message_content
