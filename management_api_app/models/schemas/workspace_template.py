from typing import List
from pydantic import BaseModel

from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate, Parameter


def get_sample_workspace_template_object(template_name: str = "tre-workspace-vanilla") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        description="vanilla workspace bundle",
        version="0.1.0",
        parameters=[
            Parameter(name="location", type="string"),
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


class WorkspaceTemplateInResponse(BaseModel):
    workspaceTemplate: ResourceTemplate

    class Config:
        schema_extra = {
            "example": {
                "workspaceTemplate": get_sample_workspace_template()
            }
        }
