
from typing import List

from pydantic import BaseModel, Field
from models.domain.restricted_resource import RestrictedResource

from models.domain.resource import ResourceType
from models.domain.shared_service import SharedService


def get_sample_shared_service(shared_service_id: str) -> dict:
    return {
        "id": shared_service_id,
        "templateName": "tre-shared-service-firewall",
        "templateVersion": "0.1.0",
        "properties": {
            "display_name": "My shared service",
            "description": "Some description",
        },
        "resourceType": ResourceType.SharedService
    }


class SharedServiceInResponse(BaseModel):
    sharedService: SharedService

    class Config:
        schema_extra = {
            "example": {
                "shared_service": get_sample_shared_service("2fdc9fba-726e-4db6-a1b8-9018a2165748")
            }
        }


class RestrictedSharedServiceInResponse(BaseModel):
    sharedService: RestrictedResource

    class Config:
        schema_extra = {
            "example": {
                "shared_service": get_sample_shared_service("2fdc9fba-726e-4db6-a1b8-9018a2165748")
            }
        }


class RestrictedSharedServicesInList(BaseModel):
    sharedServices: List[RestrictedResource] = Field([], title="shared services")

    class Config:
        schema_extra = {
            "example": {
                "sharedServices": [
                    get_sample_shared_service("2fdc9fba-726e-4db6-a1b8-9018a2165748"),
                    get_sample_shared_service("abcc9fba-726e-4db6-a1b8-9018a2165748")
                ]
            }
        }


class SharedServicesInList(BaseModel):
    sharedServices: List[SharedService] = Field([], title="shared services")

    class Config:
        schema_extra = {
            "example": {
                "sharedServices": [
                    get_sample_shared_service("2fdc9fba-726e-4db6-a1b8-9018a2165748"),
                    get_sample_shared_service("abcc9fba-726e-4db6-a1b8-9018a2165748")
                ]
            }
        }


class SharedServiceInCreate(BaseModel):
    templateName: str = Field(title="Shared service type", description="Bundle name")
    properties: dict = Field({}, title="Shared service parameters", description="Values for the parameters required by the shared service resource specification")

    class Config:
        schema_extra = {
            "example": {
                "templateName": "tre-shared-service-firewall",
                "properties": {
                    "display_name": "My shared service",
                    "description": "Some description",
                }
            }
        }
