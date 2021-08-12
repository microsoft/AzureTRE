from pydantic import BaseModel, Field

from models.domain.resource import ResourceType
from models.domain.user_resource import UserResource


def get_sample_user_resource(user_resource_id: str) -> dict:
    return {"id": user_resource_id,
            "workspaceId": "7289ru33-7265-4b5f-9eae-a1a62928772e",
            "parentWorkspaceServiceId": "e75f1ee1-9f55-414c-83da-aff677669249",
            "resourceTemplateName": "vm",
            "resourceTemplateVersion": "0.1.0",
            "resourceTemplateParameters": {
                "display_name": "my user resource",
                "description": "some description",
            },
            "deployment": {
                "status": "not_deployed",
                "message": "This resource is not yet deployed"
            },
            "deleted": False,
            "resourceType": ResourceType.UserResource
            }


class UserResourceInResponse(BaseModel):
    userResource: UserResource

    class Config:
        schema_extra = {
            "example": {
                "user_resource": get_sample_user_resource("933ad738-7265-4b5f-9eae-a1a62928772e")
            }
        }


class UserResourceInCreate(BaseModel):
    userResourceType: str = Field(title="User resource type", description="Bundle name")
    properties: dict = Field({}, title="User resource parameters",
                             description="Values for the parameters required by the user resource specification")

    class Config:
        schema_extra = {
            "example": {
                "userResourceType": "guacamole",
                "properties": {
                    "display_name": "my user resource",
                    "description": "some description",
                }
            }
        }


class UserResourceIdInResponse(BaseModel):
    resourceId: str

    class Config:
        schema_extra = {
            "example": {
                "resourceId": "49a7445c-aae6-41ec-a539-30dfa90ab1ae",
            }
        }
