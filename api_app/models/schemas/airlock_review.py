from pydantic import BaseModel, Field
from models.domain.airlock_review import AirlockReview, AirlockReviewDecision
from models.domain.airlock_resource import AirlockResourceType


def get_sample_airlock_review(workspace_id: str, airlock_request_id: str, airlock_review_id: str) -> dict:
    return {
        "reviewId": airlock_review_id,
        "requestId": airlock_request_id,
        "workspaceId": workspace_id,
        "reviewDecision": "Describe why the request was approved/rejected",
        "decisionExplanation": "Describe why the request was approved/rejected",
        "override": "false",
        "overrideJustification": "explanation",
        "allowBlockeContent": "false",
        "allowBlockedJustification": "explanation",
        "resourceType": AirlockResourceType.AirlockReview
    }


class AirlockReviewInResponse(BaseModel):
    airlock_review: AirlockReview

    class Config:
        schema_extra = {
            "example": {
                "airlock_review": get_sample_airlock_review("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef", "5c8c3430-b362-4e38-8270-441ca4381739")
            }
        }


class AirlockReviewInCreate(BaseModel):
    reviewDecision: AirlockReviewDecision = Field("", title="Airlock review decision", description="Airlock review decision")
    decisionExplanation: str = Field("Decision Explanation", title="Explanation of the reviewer for the reviews decision")

    class Config:
        schema_extra = {
            "example": {
                "reviewDecision": "approved",
                "decisionExplanation": "the reason why this request was approved/rejected"
            }
        }
