from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate, Property
from models.schemas.resource_template import ResourceTemplateInCreate, ResourceTemplateInResponse


def get_sample_workspace_template_object(template_name: str = "tre-workspace-base") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        description="base workspace bundle",
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
                    "title": "My Workspace Template Custom Parameters",
                    "description": "These parameters are specific to my workspace template",
                    "required": [
                        "vm_size",
                        "no_of_vms"
                    ],
                    "properties": {
                        "vm_size": {
                            "$id": "#/properties/vm_size",
                            "type": "string",
                            "title": "VM size",
                            "description": "Size of the VMs in my workspace",
                            "default": "Standard_A1",
                            "enum": [
                                "Standard_A1",
                                "Standard_A2",
                                "Standard_A3"
                            ]
                        },
                        "no_of_vms": {
                            "$id": "#/properties/no_of_vms",
                            "type": "integer",
                            "title": "Number of VMs",
                            "description": "Number of virtual machines to be deployed in the workspace",
                            "default": 0
                        }
                    }
                }
            }
        }


class WorkspaceTemplateInResponse(ResourceTemplateInResponse):

    class Config:
        schema_extra = {
            "example": get_sample_workspace_template_in_response()
        }
