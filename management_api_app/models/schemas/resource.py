from typing import List
from pydantic import BaseModel

from models.domain.resource import Resource


class ResourceInResponse(BaseModel):
    resource: Resource


class ResourcesInList(BaseModel):
    resources: List[Resource]


class WorkspaceInCreate(BaseModel):
    description: str
    resourceSpecId: str
    data: str
    adminUserIdOrEmail: str
