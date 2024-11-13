from typing import List

from pydantic import BaseModel, Field

from models.domain.resource import ResourceType
from models.domain.workspace_service import WorkspaceService


def get_sample_workspace_service(workspace_id: str, workspace_service_id: str) -> dict:
    return {
        "id": workspace_service_id,
        "workspaceId": workspace_id,
        "templateName": "guacamole",
        "templateVersion": "0.1.0",
        "properties": {
            "display_name": "my workspace service",
            "description": "some description",
        },
        "resourceType": ResourceType.WorkspaceService
    }


class WorkspaceServiceInResponse(BaseModel):
    workspaceService: WorkspaceService

    class Config:
        schema_extra = {
            "example": {
                "workspace_service": get_sample_workspace_service("933ad738-7265-4b5f-9eae-a1a62928772e", "2fdc9fba-726e-4db6-a1b8-9018a2165748")
            }
        }


class WorkspaceServicesInList(BaseModel):
    workspaceServices: List[WorkspaceService] = Field([], title="Workspace services")

    class Config:
        schema_extra = {
            "example": {
                "workspaceServices": [
                    get_sample_workspace_service("933ad738-7265-4b5f-9eae-a1a62928772e", "2fdc9fba-726e-4db6-a1b8-9018a2165748"),
                    get_sample_workspace_service("933ad738-7265-4b5f-9eae-a1a62928772e", "abcc9fba-726e-4db6-a1b8-9018a2165748")
                ]
            }
        }


class WorkspaceServiceInCreate(BaseModel):
    templateName: str = Field(title="Workspace service type", description="Bundle name")
    properties: dict = Field({}, title="Workspace service parameters", description="Values for the parameters required by the workspace service resource specification")

    class Config:
        schema_extra = {
            "example": {
                "templateName": "tre-service-guacamole",
                "properties": {
                    "display_name": "my workspace service",
                    "description": "some description",
                }
            }
        }
