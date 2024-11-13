from pydantic import Field

from models.domain.resource import ResourceType
from models.domain.resource_template import CustomAction, Property
from models.domain.user_resource_template import UserResourceTemplate
from models.schemas.resource_template import ResourceTemplateInCreate, ResourceTemplateInResponse


def get_sample_user_resource_template_object(template_name: str = "guacamole-vm") -> UserResourceTemplate:
    return UserResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        title="Guacamole VM",
        parentWorkspaceService="guacamole",
        description="user resource bundle",
        version="0.1.0",
        resourceType=ResourceType.UserResource,
        current=True,
        type="object",
        required=["display_name", "description"],
        properties={
            "display_name": Property(type="string"),
            "description": Property(type="string")
        },
        customActions=[CustomAction()]
    )


def get_sample_user_resource_template() -> dict:
    return get_sample_user_resource_template_object().dict()


def get_sample_user_resource_template_in_response() -> dict:
    workspace_template = get_sample_user_resource_template()
    return workspace_template


class UserResourceTemplateInCreate(ResourceTemplateInCreate):

    class Config:
        schema_extra = {
            "example": {
                "name": "my-tre-user-resource",
                "version": "0.0.1",
                "current": "true",
                "json_schema": {
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "$id": "https://github.com/microsoft/AzureTRE/templates/workspaces/myworkspace/user_resource.json",
                    "type": "object",
                    "title": "My User Resource Template",
                    "description": "These is a test user resource template schema",
                    "required": [],
                    "authorizedRoles": [],
                    "properties": {},
                },
                "customActions": [
                    {
                        "name": "start",
                        "description": "Starts a VM"
                    },
                    {
                        "name": "stop",
                        "description": "Stops a VM"
                    }
                ]
            }
        }


class UserResourceTemplateInResponse(ResourceTemplateInResponse):
    parentWorkspaceService: str = Field(title="Workspace type", description="Bundle name")

    class Config:
        schema_extra = {
            "example": get_sample_user_resource_template_in_response()
        }
