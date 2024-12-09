from pydantic import Field

from models.domain.resource import Resource, ResourceType


class WorkspaceService(Resource):
    """
    Workspace service request
    """
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    resourceType: ResourceType = ResourceType.WorkspaceService
