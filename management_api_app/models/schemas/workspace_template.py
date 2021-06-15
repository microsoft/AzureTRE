from typing import List
from pydantic import BaseModel, Field

from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate, Parameter


def get_sample_workspace_template_object(template_name: str = "tre-workspace-vanilla") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        description="vanilla workspace bundle",
        version="0.1.0",
        parameters=[
            Parameter(name="azure_location", type="string"),
            Parameter(name="tre_id", type="string"),
            Parameter(name="workspace_id", type="string"),
            Parameter(name="address_space", type="string", default="10.2.1.0/24", description="VNet address space for the workspace services")
        ],
        resourceType=ResourceType.Workspace,
        current=True,
    )


def get_sample_workspace_template() -> dict:
    return get_sample_workspace_template_object().dict()


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
    parameters: List[Parameter] = Field([], title="Workspace template parameters", description="Values for the parameters required by the workspace template")
    current: bool = Field(title="Mark this version as current")

    class Config:
        schema_extra = {
            "example": {
                "name": "my-tre-workspace",
                "version": "0.0.1",
                "description": "workspace template for great product",
                "parameters": [{
                    "name": "azure_location",
                    "type": "string"
                }],
                "current": "true"
            }
        }


class WorkspaceTemplateInResponse(BaseModel):
    workspaceTemplate: ResourceTemplate

    class Config:
        schema_extra = {
            "example": {
                "resourceTemplateId": "49a7445c-aae6-41ec-a539-30dfa90ab1ae",
                "workspaceTemplate": get_sample_workspace_template()
            }
        }
