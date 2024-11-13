from models.domain.resource import ResourceType
from models.domain.resource_template import ResourceTemplate, Property, CustomAction
from models.schemas.resource_template import ResourceTemplateInCreate, ResourceTemplateInResponse


def get_sample_shared_service_template_object(template_name: str = "tre-shared-service") -> ResourceTemplate:
    return ResourceTemplate(
        id="a7a7a7bd-7f4e-4a4e-b970-dc86a6b31dfb",
        name=template_name,
        title="Shared Service",
        description="Shared service bundle",
        version="0.1.0",
        resourceType=ResourceType.SharedService,
        current=True,
        type="object",
        required=["display_name", "description"],
        properties={
            "display_name": Property(type="string"),
            "description": Property(type="string")
        },
        actions=[CustomAction()]
    )


def get_sample_shared_service_template() -> dict:
    return get_sample_shared_service_template_object().dict()


def get_sample_shared_service_template_in_response() -> dict:
    shared_template = get_sample_shared_service_template()
    shared_template["system_properties"] = {
        "tre_id": Property(type="string"),
        "shared_service_id": Property(type="string"),
        "azure_location": Property(type="string"),
    }
    return shared_template


class SharedServiceTemplateInCreate(ResourceTemplateInCreate):
    class Config:
        schema_extra = {
            "example": {
                "name": "my-tre-shared-service",
                "version": "0.0.1",
                "current": "true",
                "json_schema": {
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "$id": "https://github.com/microsoft/AzureTRE/templates/shared_services/myshared_service/shared_service.json",
                    "type": "object",
                    "title": "My Shared Service Template",
                    "description": "These is a test shared service resource template schema",
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


class SharedServiceTemplateInResponse(ResourceTemplateInResponse):
    class Config:
        schema_extra = {
            "example": get_sample_shared_service_template_in_response()
        }
