from enum import StrEnum
from typing import List

from pydantic import BaseModel, Field

from models.domain.resource import ResourceType
from models.domain.workspace import Workspace, WorkspaceAuth


def get_sample_workspace(workspace_id: str, spec_workspace_id: str = "0001") -> dict:
    return {
        "id": workspace_id,
        "templateName": "tre-workspace-base",
        "templateVersion": "0.1.0",
        "properties": {
            "azure_location": "westeurope",
            "workspace_id": spec_workspace_id,
            "tre_id": "mytre-dev-1234",
            "address_space_size": "small",
        },
        "resourceType": ResourceType.Workspace,
        "workspaceURL": ""
    }


class AuthProvider(StrEnum):
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


class WorkspaceAuthInResponse(BaseModel):
    workspaceAuth: WorkspaceAuth

    class Config:
        schema_extra = {
            "example": {
                "scopeId": "api://mytre-ws-1233456"
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
    templateName: str = Field(title="Workspace type", description="Bundle name")
    properties: dict = Field({}, title="Workspace parameters", description="Values for the parameters required by the workspace resource specification")

    class Config:
        schema_extra = {
            "example": {
                "templateName": "tre-workspace-base",
                "properties": {
                    "display_name": "the workspace display name",
                    "description": "workspace description",
                    "auth_type": "Manual",
                    "client_id": "<WORKSPACE_CLIENT_ID>",
                    "client_secret": "<WORKSPACE_CLIENT_SECRET>",
                    "address_space_size": "small"
                }
            }
        }
