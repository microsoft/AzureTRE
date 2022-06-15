from pydantic import BaseModel, Field
from models.domain.airlock_resource import AirlockResourceType
from models.domain.airlock_request import AirlockRequest, AirlockRequestType


def get_sample_airlock_request(workspace_id: str, airlock_request_id: str) -> dict:
    return {
        "requestId": airlock_request_id,
        "workspaceId": workspace_id,
        "status": "draft",
        "requestType": "import",
        "files": [],
        "businessJustification": "some business justification",
        "resourceType": AirlockResourceType.AirlockRequest
    }


class AirlockRequestInResponse(BaseModel):
    airlock_request: AirlockRequest

    class Config:
        schema_extra = {
            "example": {
                "airlock_request": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestInCreate(BaseModel):
    requestType: AirlockRequestType = Field("", title="Airlock request type", description="Specifies if this is an import or an export request")
    businessJustification: str = Field("Business Justifications", title="Explanation that will be provided to the request reviewer")
    properties: dict = Field({}, title="Airlock request parameters", description="Values for the parameters required by the Airlock request specification")

    class Config:
        schema_extra = {
            "example": {
                "requestType": "import",
                "businessJustification": "some business justification"
            }
        }
