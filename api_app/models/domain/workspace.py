from enum import Enum
from pydantic import Field
from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import Resource, ResourceType


class WorkspaceRole(Enum):
    NoRole = 0
    Researcher = 1
    Owner = 2
    AirlockManager = 3


class Workspace(Resource):
    """
    Workspace request
    """
    workspaceURL: str = Field("", title="Workspace URL", description="Main endpoint for workspace users")
    resourceType: ResourceType = ResourceType.Workspace


class WorkspaceAuth(AzureTREModel):
    scopeId: str = Field("", title="Scope ID", description="The Workspace App Scope Id to use for auth")
