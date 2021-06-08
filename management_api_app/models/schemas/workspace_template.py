from typing import List
from pydantic import BaseModel, Field


class WorkspaceTemplateNamesInList(BaseModel):
    templateNames: List[str]

    class Config:
        schema_extra = {
            "example": {
                "templateNames": ["tre-workspace-vanilla", "tre-workspace-base"]
            }
        }


class WorkspaceTemplateInCreate(BaseModel):

    name: str = Field(title="Name of workspace template")
    version: str = Field(title="Version of workspace template")
    description: str = Field(title=" Description of workspace template")
    properties: dict = Field({}, title="Workspace template properties",
                             description="Values for the properties required by the workspace template")
    resourceType: str = Field(title="Type of workspace template")
    current: bool = Field(title="Mark this version as current")

    class Config:
        schema_extra = {
            "example": {
                "name": "My workspace template",
                "version": "0.0.1",
                "description": "workspace template for great product",
                "properties": {},
                "resourceType": "workspace",
                "current": "true"
            }
        }


class WorkspaceTemplateIdInResponse(BaseModel):
    resourceTemplateId: str

    class Config:
        schema_extra = {
            "example": {
                "resourceTemplateId": "49a7445c-aae6-41ec-a539-30dfa90ab1ae",
            }
        }
