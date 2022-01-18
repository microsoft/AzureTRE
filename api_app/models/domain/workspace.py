from enum import Enum
from typing import List

from pydantic import Field
from pydantic.types import UUID4

from models.domain.azuretremodel import AzureTREModel
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
    authInformation: dict = Field({})
