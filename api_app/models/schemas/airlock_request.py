from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from models.domain.airlock_request import AirlockRequest, AirlockRequestType


def get_sample_airlock_review(airlock_review_id: str) -> dict:
    return {
        "reviewId": airlock_review_id,
        "reviewDecision": "Describe why the request was approved/rejected",
        "decisionExplanation": "Describe why the request was approved/rejected"
    }


def get_sample_airlock_request(workspace_id: str, airlock_request_id: str) -> dict:
    return {
        "requestId": airlock_request_id,
        "workspaceId": workspace_id,
        "status": "draft",
        "requestType": "import",
        "files": [],
        "businessJustification": "some business justification",
        "creationTime": datetime.utcnow().timestamp(),
        "reviews": [
            get_sample_airlock_review("29990431-5451-40e7-a58a-02e2b7c3d7c8"),
            get_sample_airlock_review("02dc0f29-351a-43ec-87e7-3dd2b5177b7f")]
    }


class AirlockRequestInResponse(BaseModel):
    airlockRequest: AirlockRequest

    class Config:
        schema_extra = {
            "example": {
                "airlock_request": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestInList(BaseModel):
    airlockRequests: List[AirlockRequest] = Field([], title="Airlock Requests")

    class Config:
        schema_extra = {
            "example": {
                "airlock_requests": [
                    get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef"),
                    get_sample_airlock_request("123ad738-1234-4b5f-9eae-a1a62928772e", "457e921f-a4aa-44b3-90a9-e8da030412ac"),
                ]
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


class AirlockReviewInCreate(BaseModel):
    approval: bool = Field("", title="Airlock review decision", description="Airlock review decision")
    decisionExplanation: str = Field("Decision Explanation", title="Explanation of the reviewer for the reviews decision")

    class Config:
        schema_extra = {
            "example": {
                "approval": "True",
                "decisionExplanation": "the reason why this request was approved/rejected"
            }
        }
