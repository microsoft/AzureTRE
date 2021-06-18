from pydantic import Field
from pydantic.types import UUID4
from models.domain.azuretremodel import AzureTREModel

from models.domain.resource import Resource, ResourceType, Status


class DeploymentStatusUpdateMessage(AzureTREModel):
    id: UUID4 = Field(title="", description="")
    status: Status = Field(title="", description="")
    message: str = Field(title="", description="")


class Workspace(Resource):
    """
    Workspace request
    """
    workspaceURL: str = Field("", title="Workspace URL", description="Main endpoint for workspace users")
    resourceType = ResourceType.Workspace
