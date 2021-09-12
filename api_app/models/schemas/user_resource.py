from typing import List

from pydantic import BaseModel, Field

from models.domain.resource import ResourceType
from models.domain.user_resource import UserResource


def get_sample_user_resource(user_resource_id: str) -> dict:
    return {
        "id": user_resource_id,
        "ownerId": "abc9ru33-7265-4b5f-9eae-a1a62928772e",
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


class UserResourcesInList(BaseModel):
    userResources: List[UserResource] = Field([], title="User resources")

    class Config:
        schema_extra = {
            "example": {
                "userResources": [
                    get_sample_user_resource("2fdc9fba-726e-4db6-a1b8-9018a2165748"),
                    get_sample_user_resource("abcc9fba-726e-4db6-a1b8-9018a2165748")
                ]
            }
        }


class UserResourceInCreate(BaseModel):
    userResourceType: str = Field(title="User resource type", description="Bundle name")
    properties: dict = Field({}, title="User resource parameters", description="Values for the parameters required by the user resource specification")

    class Config:
        schema_extra = {
            "example": {
                "userResourceType": "user-resource-type",
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

class UserResourcePatchEnabled(BaseModel):
    enabled: bool

    class Config:
        schema_extra = {
            "example": {
                "enabled": False
            }
        }
