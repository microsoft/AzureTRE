from enum import Enum
from typing import List
from pydantic import BaseModel, Field

from models.domain.workspace import Workspace


def get_sample_workspace(workspace_id: str, spec_workspace_id: str = "0001") -> dict:
    return {
        "id": workspace_id,
        "workspaceId": "7289ru33-7265-4b5f-9eae-a1a62928772e",
        "displayName": "my workspace",
        "description": "some description",
        "resourceTemplateName": "tre-workspace-vanilla",
        "resourceTemplateVersion": "0.1.0",
        "resourceTemplateParameters": {
            "azure_location": "westeurope",
            "workspace_id": spec_workspace_id,
            "tre_id": "mytre-dev-1234",
            "address_space": "10.2.1.0/24"
        },
        "deployment": {
            "status": "not_deployed",
            "message": "This resource is not yet deployed"
        },
        "isDeleted": False,
        "resourceType": "workspace",
        "workspaceURL": "",
        "authInformation": {}
    }


class WorkspaceInResponse(BaseModel):
    workspace: Workspace

    class Config:
        schema_extra = {
            "example": {
                "workspace": get_sample_workspace("933ad738-7265-4b5f-9eae-a1a62928772e")
            }
        }


class WorkspaceServiceInCreate(BaseModel):
    workspaceServiceType: str = Field(title="Workspace service type", description="Bundle name")
    properties: dict = Field({}, title="Workspace service parameters", description="Values for the parameters required by the workspace resource specification")

    class Config:
        schema_extra = {
            "example": {
                "workspaceServiceType": "guacamole",
                "properties": {}
            }
        }


class WorkspaceServiceIdInResponse(BaseModel):
    workspaceId: str

    class Config:
        schema_extra = {
            "example": {
                "workspaceServiceId": "49a7445c-aae6-41ec-a539-30dfa90ab1ae",
            }
        }
