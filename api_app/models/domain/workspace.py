from enum import Enum
from typing import Optional
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
    siblingWorkspaceId: Optional[str] = Field(None, title="Sibling Workspace ID", description="ID of a related sibling workspace")
    resourceType: ResourceType = ResourceType.Workspace


class WorkspaceAuth(AzureTREModel):
    scopeId: str = Field("", title="Scope ID", description="The Workspace App Scope Id to use for auth")
