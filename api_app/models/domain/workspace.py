from enum import Enum
from pydantic import Field
from models.domain.resource import Resource, ResourceType


class WorkspaceRole(Enum):
    NoRole = 0
    Researcher = 1
    Owner = 2


class Workspace(Resource):
    """
    Workspace request
    """
    workspaceURL: str = Field("", title="Workspace URL", description="Main endpoint for workspace users")
    resourceType = ResourceType.Workspace
