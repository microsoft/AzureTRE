from pydantic import Field
from models.domain.airlock_request import AirlockRequestStatus
from models.domain.airlock_resource import AirlockResource, AirlockResourceType


class AirlockReviewDecision(str):
    Approved = AirlockRequestStatus.Approved
    Rejected = AirlockRequestStatus.Rejected


class AirlockReview(AirlockResource):
    """
    Airlock review
    """
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    requestId: str = Field("", title="Airlock Request ID", description="Service target Airlock id")
    resourceType = AirlockResourceType.AirlockReview
    reviewDecision: AirlockReviewDecision = Field("", title="Airlock review decision")
    decisionExplanation: str = Field(False, title="Explanation why the request was approved/rejected")
    override: bool = Field(False, title="Override a review")
    overrideJustification: str = Field("", title="Explanation why we allow overriding a review")
    allowBlockedContent: bool = Field(False, title="Allowing blocked content")
    allowBlockedJustification: str = Field("", title="Explanation why we allow block content")
