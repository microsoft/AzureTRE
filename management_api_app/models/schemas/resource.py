from typing import List
from pydantic import BaseModel

from models.domain.resource import Resource, ResourceSpec


class ResourceInResponse(BaseModel):
    resource: Resource


class ResourcesInList(BaseModel):
    resources: List[Resource]


class ResourceInCreate(BaseModel):
    resourceSpec: ResourceSpec
    parameters: dict
