from pydantic import BaseModel, Field
from models.domain.airlock_resource import AirlockResourceType
from models.domain.airlock_request import AirlockRequest


def get_sample_airlock_request(workspace_id: str, airlock_request_id: str) -> dict:
    return {
        "requestId": airlock_request_id,
        "workspaceId": workspace_id,
        "isActive": True,
        "requestType": "import",
        "files": [],
        "business_justification": "some business justification",
        "status": "draft",
        "properties": {
            "display_name": "my workspace service",
            "description": "some description",
        },
        "container": [{
            "id": "containerid",
            "type": "external",
            "connectionstring": "https://externalstoragexyz.blob.core.windows.net/<ws_id>?sp=...XYZ"
        }],
        "resourceType": AirlockResourceType.AirlockRequest
    }


class AirlockRequestInResponse(BaseModel):
    AirlockRequest: AirlockRequest

    class Config:
        schema_extra = {
            "example": {
                "airlock_request": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestInCreate(BaseModel):
    properties: dict = Field({}, title="Airlock request parameters", description="Values for the parameters required by the Airlock request specification")

    class Config:
        schema_extra = {
            "example": {
                "properties": {
                    "type": "import",
                    "business_justification": "some business justification",
                }
            }
        }
