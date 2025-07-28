from pydantic import Field

from models.domain.resource import Resource, ResourceType


class UserResource(Resource):
    """
    User resource
    """
    workspaceId: str = Field(default="", title="Workspace ID", description="Service target Workspace id")
    ownerId: str = Field(default="", title="Owner of the user resource")
    parentWorkspaceServiceId: str = Field(default="", title="Parent Workspace Service ID", description="Service target Workspace Service id")
    azureStatus: dict = Field({}, title="Azure Status", description="Azure status, varies per user resource")
    resourceType: ResourceType = ResourceType.UserResource
