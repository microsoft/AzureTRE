from pydantic import BaseModel, Field

from models.domain.resource import ResourceType
from models.domain.workspace_service import WorkspaceService


def get_sample_workspace_service(workspace_id: str) -> dict:
    return {"id": workspace_id,
            "workspaceId": "7289ru33-7265-4b5f-9eae-a1a62928772e",
            "resourceTemplateName": "guacamole",
            "resourceTemplateVersion": "0.1.0",
            "resourceTemplateParameters": {
                "display_name": "my workspace service",
                "description": "some description",
            },
            "deployment": {
                "status": "not_deployed",
                "message": "This resource is not yet deployed"
            },
            "deleted": False,
            "resourceType": ResourceType.WorkspaceService,
            "workspaceURL": "",
            "authInformation": {}
            }


class WorkspaceServiceInResponse(BaseModel):
    workspaceService: WorkspaceService

    class Config:
        schema_extra = {
            "example": {
                "workspace": get_sample_workspace_service("933ad738-7265-4b5f-9eae-a1a62928772e")
            }
        }


class WorkspaceServiceInCreate(BaseModel):
    workspaceServiceType: str = Field(title="Workspace service type", description="Bundle name")
    properties: dict = Field({}, title="Workspace service parameters",
                             description="Values for the parameters required by the workspace resource specification")

    class Config:
        schema_extra = {
            "example": {
                "workspaceServiceType": "guacamole",
                "properties": {
                    "display_name": "my workspace service",
                    "description": "some description",
                }
            }
        }


class WorkspaceServiceIdInResponse(BaseModel):
    workspaceServiceId: str

    class Config:
        schema_extra = {
            "example": {
                "workspaceServiceId": "49a7445c-aae6-41ec-a539-30dfa90ab1ae",
            }
        }
