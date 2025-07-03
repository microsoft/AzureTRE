import uuid
from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field
from models.domain.operation import Operation
from models.schemas.operation import get_sample_operation
from models.domain.airlock_request import AirlockActions, AirlockRequest, AirlockRequestType


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
        "type": "import",
        "files": [],
        "title": "a request title",
        "businessJustification": "some business justification",
        "createdBy": {
            "id": "a user id",
            "name": "a user name"
        },
        "createdWhen": datetime.now(timezone.utc).timestamp(),
        "reviews": [
            get_sample_airlock_review("29990431-5451-40e7-a58a-02e2b7c3d7c8"),
            get_sample_airlock_review("02dc0f29-351a-43ec-87e7-3dd2b5177b7f")]
    }


def get_sample_airlock_request_with_allowed_user_actions(workspace_id: str) -> dict:
    return {
        "airlockRequest": get_sample_airlock_request(workspace_id, str(uuid.uuid4())),
        "allowedUserActions": [AirlockActions.Cancel, AirlockActions.Review, AirlockActions.Submit],
    }


class AirlockRequestInResponse(BaseModel):
    airlockRequest: AirlockRequest

    class Config:
        schema_extra = {
            "example": {
                "airlockRequest": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestAndOperationInResponse(BaseModel):
    airlockRequest: AirlockRequest
    operation: Operation

    class Config:
        schema_extra = {
            "example": {
                "airlockRequest": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef"),
                "operation": get_sample_operation("121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestWithAllowedUserActions(BaseModel):
    airlockRequest: AirlockRequest = Field([], title="Airlock Request")
    allowedUserActions: List[str] = Field([], title="actions that the requesting user can do on the request")

    class Config:
        schema_extra = {
            "example": get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e"),
        }


class AirlockRequestWithAllowedUserActionsInList(BaseModel):
    airlockRequests: List[AirlockRequestWithAllowedUserActions] = Field([], title="Airlock Requests")

    class Config:
        schema_extra = {
            "example": {
                "airlockRequests": [
                    get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e"),
                    get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e")
                ]
            }
        }


class AirlockRequestInCreate(BaseModel):
    type: AirlockRequestType = Field("", title="Airlock request type", description="Specifies if this is an import or an export request")
    title: str = Field("Airlock Request", title="Brief title for the request")
    businessJustification: str = Field("Business Justifications", title="Explanation that will be provided to the request reviewer")
    properties: dict = Field({}, title="Airlock request parameters", description="Values for the parameters required by the Airlock request specification")

    class Config:
        schema_extra = {
            "example": {
                "type": "import",
                "title": "a request title",
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


class AirlockRevokeInCreate(BaseModel):
    reason: str = Field(title="Reason for revoking the approved request")

    class Config:
        schema_extra = {
            "example": {
                "reason": "Request was approved in error or security concerns identified"
            }
        }
