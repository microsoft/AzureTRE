from models.domain.resource import ResourceType
from models.domain.resource_template import CustomAction, ResourceTemplate, Property
from models.schemas.resource_template import ResourceTemplateInCreate, ResourceTemplateInResponse


def get_sample_workspace_template_object(template_name: str = "tre-workspace-base") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        title="Workspace",
        description="base workspace bundle",
        version="0.1.0",
        resourceType=ResourceType.Workspace,
        current=True,
        type="object",
        required=["display_name", "description", "client_id"],
        properties={
            "display_name": Property(type="string"),
            "description": Property(type="string"),
            "client_id": Property(type="string"),
            "client_secret": Property(type="string"),
            "address_space_size": Property(
                type="string",
                default="small",
                description="This can have a value of small, medium, large or custom. If you specify custom, then you need to specify a VNet address space in 'address_space' (e.g. 10.2.1.0/24)")
        },
        customActions=[
            CustomAction()
        ]
    )


def get_sample_workspace_template_in_response() -> dict:
    workspace_template = get_sample_workspace_template_object().dict()
    workspace_template["system_properties"] = {
        "tre_id": Property(type="string"),
        "workspace_id": Property(type="string"),
        "azure_location": Property(type="string"),
    }
    return workspace_template


class WorkspaceTemplateInCreate(ResourceTemplateInCreate):

    class Config:
        schema_extra = {
            "example": {
                "name": "my-tre-workspace",
                "version": "0.0.1",
                "current": "true",
                "json_schema": {
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/workspace.json",
                    "type": "object",
                    "title": "My Workspace Template",
                    "description": "This is a test workspace template schema",
                    "required": [
                        "vm_size",
                        "no_of_vms"
                    ],
                    "authorizedRoles": [],
                    "properties": {
                        "display_name": {
                            "type": "string",
                            "title": "Name for the workspace",
                            "description": "The name of the workspace to be displayed to users"
                        },
                        "description": {
                            "type": "string",
                            "title": "Description of the workspace",
                            "description": "Description of the workspace"
                        },
                        "address_space_size": {
                            "type": "string",
                            "title": "Address space size",
                            "description": "Network address size (small, medium, large or custom) to be used by the workspace"
                        },
                        "address_space": {
                            "type": "string",
                            "title": "Address space",
                            "description": "Network address space to be used by the workspace if address_space_size is custom"
                        }
                    }
                },
                "customActions": [
                    {
                        "name": "disable",
                        "description": "Deallocates resources"
                    }
                ]
            }
        }


class WorkspaceTemplateInResponse(ResourceTemplateInResponse):

    class Config:
        schema_extra = {
            "example": get_sample_workspace_template_in_response()
        }
