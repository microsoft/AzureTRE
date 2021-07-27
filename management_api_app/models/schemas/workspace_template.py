from typing import List, Dict
from pydantic import BaseModel, Field

from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate, Property


def get_sample_workspace_template_object(template_name: str = "tre-workspace-vanilla") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        description="vanilla workspace bundle",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        type="object",
        required=["display_name", "description", "app_id"],
        properties={
            "display_name": Property(type="string"),
            "description": Property(type="string"),
            "app_id": Property(type="string"),
            "address_space": Property(type="string", default="10.2.1.0/24", description="VNet address space for the workspace services")
        }
    )


def get_sample_workspace_template() -> dict:
    return get_sample_workspace_template_object().dict()


def get_sample_workspace_template_in_response() -> dict:
    workspace_template = get_sample_workspace_template_object().dict()
    workspace_template["system_properties"] = {
        "tre_id": Property(type="string"),
        "workspace_id": Property(type="string"),
        "azure_location": Property(type="string"),
    }
    return workspace_template


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
    parameters: List[Property] = Field([], title="Workspace template parameters", description="Values for the parameters required by the workspace template")
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


class WorkspaceTemplateInResponse(ResourceTemplate):
    system_properties: Dict[str, Property] = Field(title="System properties")

    class Config:
        schema_extra = {
            "example": get_sample_workspace_template_in_response()
        }
