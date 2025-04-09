from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate, Property, CustomAction
from models.schemas.resource_template import ResourceTemplateInCreate, ResourceTemplateInResponse


def get_sample_workspace_service_template_object(template_name: str = "tre-workspace-service") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        title="Workspace Service",
        description="workspace service bundle",
        version="0.1.0",
        resourceType=ResourceType.WorkspaceService,
        current=True,
        type="object",
        required=["display_name", "description"],
        properties={
            "display_name": Property(type="string"),
            "description": Property(type="string")
        },
        customActions=[CustomAction()]
    )


def get_sample_workspace_service_template() -> dict:
    return get_sample_workspace_service_template_object().dict()


def get_sample_workspace_service_template_in_response() -> dict:
    workspace_template = get_sample_workspace_service_template()
    workspace_template["system_properties"] = {
        "tre_id": Property(type="string"),
        "workspace_id": Property(type="string"),
        "azure_location": Property(type="string"),
    }
    return workspace_template


class WorkspaceServiceTemplateInCreate(ResourceTemplateInCreate):

    class Config:
        schema_extra = {
            "example": {
                "name": "my-tre-workspace-service",
                "version": "0.0.1",
                "current": "true",
                "json_schema": {
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/workspace_service.json",
                    "type": "object",
                    "title": "My Workspace Service Template",
                    "description": "These is a test workspace service resource template schema",
                    "required": [],
                    "authorizedRoles": [],
                    "properties": {}
                },
                "customActions": [
                    {
                        "name": "disable",
                        "description": "Deallocates resources"
                    }
                ]
            }
        }


class WorkspaceServiceTemplateInResponse(ResourceTemplateInResponse):

    class Config:
        schema_extra = {
            "example": get_sample_workspace_service_template_in_response()
        }
