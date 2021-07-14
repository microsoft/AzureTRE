from enum import Enum
from typing import List
from pydantic import BaseModel, Field

from models.domain.workspace import Workspace


def get_sample_workspace(workspace_id: str, spec_workspace_id: str = "0001") -> dict:
    return {
        "id": workspace_id,
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


class AuthProvider(str, Enum):
    """
    Auth Provider
    """
    AAD = "AAD"


class AuthenticationConfiguration(BaseModel):
    provider: AuthProvider = Field(AuthProvider.AAD, title="Authentication Provider")
    data: dict = Field({}, title="Authentication information")


class WorkspaceInResponse(BaseModel):
    workspace: Workspace

    class Config:
        schema_extra = {
            "example": {
                "workspace": get_sample_workspace("933ad738-7265-4b5f-9eae-a1a62928772e")
            }
        }


class WorkspacesInList(BaseModel):
    workspaces: List[Workspace]

    class Config:
        schema_extra = {
            "example": {
                "workspaces": [
                    get_sample_workspace("933ad738-7265-4b5f-9eae-a1a62928772e", "0001"),
                    get_sample_workspace("2fdc9fba-726e-4db6-a1b8-9018a2165748", "0002"),
                ]
            }
        }


class WorkspaceInCreate(BaseModel):
    displayName: str = Field(title="Friendly name for workspace")
    workspaceType: str = Field(title="Workspace type", description="Bundle name")
    description: str = Field(title="Workspace description")
    parameters: dict = Field({}, title="Workspace parameters", description="Values for the parameters required by the workspace resource specification")
    authConfig: AuthenticationConfiguration = Field(title="Authentication configuration", description="Authentication configuration for the workspace")

    class Config:
        schema_extra = {
            "example": {
                "displayName": "My workspace",
                "description": "workspace for team X",
                "workspaceType": "tre-workspace-vanilla",
                "parameters": {},
                "authConfig": {
                    "provider": "AAD",
                    "data": {"app_id": "1212445c-aae6-41ec-a539-30dfa90ab1ae"}
                }
            }
        }


class WorkspaceIdInResponse(BaseModel):
    workspaceId: str

    class Config:
        schema_extra = {
            "example": {
                "workspaceId": "49a7445c-aae6-41ec-a539-30dfa90ab1ae",
            }
        }
