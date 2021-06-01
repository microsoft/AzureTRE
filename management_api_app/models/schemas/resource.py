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

    class Config:
        schema_extra = {
            "example": {
                "resourceSpec": {
                    "name": "tre-workspace-vanilla",
                    "version": "0.1.0"
                },
                "parameters": {
                    "core_id": "mytre-dev-3142",
                    "workspace_id": "2718",
                    "location": "westeurope",
                    "address_space": "10.2.1.0/24",
                }
            }
        }
