from pydantic import Field
from enum import Enum
from models.domain.airlock_resource import AirlockResource, AirlockResourceType
from resources import strings


class AirlockReviewDecision(str, Enum):
    Approved = strings.AIRLOCK_RESOURCE_STATUS_APPROVED
    Rejected = strings.AIRLOCK_RESOURCE_STATUS_REJECTED


class AirlockReview(AirlockResource):
    """
    Airlock review
    """
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    requestId: str = Field("", title="Airlock Request ID", description="Service target Airlock id")
    resourceType = AirlockResourceType.AirlockReview
    reviewDecision: AirlockReviewDecision = Field("", title="Airlock review decision")
    decisionExplanation: str = Field(False, title="Explanation why the request was approved/rejected")
