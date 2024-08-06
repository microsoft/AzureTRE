from typing import List, Optional
from pydantic import BaseModel, Field, Extra

from models.domain.resource import ResourceHistoryItem


class ResourcePatch(BaseModel):
    isEnabled: Optional[bool]
    properties: Optional[dict]
    templateVersion: Optional[str]

    class Config:
        extra = Extra.forbid
        schema_extra = {
            "example": {
                "isEnabled": False,
                "templateVersion": "1.0.1",
                "properties": {
                    "display_name": "the display name",
                    "description": "a description",
                    "other_fields": "other properties defined by the resource template"
                }
            }
        }


def get_sample_resource_history(resource_id: str) -> dict:
    return {
        "id": "abc9ru33-7265-4b5f-9eae-a1a62928772e",
        "resourceId": resource_id,
        "templateName": "vm",
        "templateVersion": "0.1.0",
        "properties": {
            "display_name": "my user resource",
            "description": "some description",
        },
        "isEnabled": "true",
        "resourceVersion": "1",
        "updatedWhen": "",
        "user": ""
    }


class ResourceHistoryInList(BaseModel):
    resource_history: List[ResourceHistoryItem] = Field([], title="Resource history")

    class Config:
        schema_extra = {
            "example": {
                "resource_history": [
                    get_sample_resource_history("2fdc9fba-726e-4db6-a1b8-9018a2165748"),
                    get_sample_resource_history("abcc9fba-726e-4db6-a1b8-9018a2165748")
                ]
            }
        }
