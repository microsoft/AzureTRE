from typing import List
from enum import Enum
from pydantic import Field
from pydantic.schema import Optional
from resources import strings
from models.domain.azuretremodel import AzureTREModel


class AirlockRequestStatus(str, Enum):
    """
    Airlock Resource status
    """
    Draft = strings.AIRLOCK_RESOURCE_STATUS_DRAFT
    Submitted = strings.AIRLOCK_RESOURCE_STATUS_SUBMITTED
    InReview = strings.AIRLOCK_RESOURCE_STATUS_INREVIEW
    ApprovalInProgress = strings.AIRLOCK_RESOURCE_STATUS_APPROVAL_INPROGRESS
    Approved = strings.AIRLOCK_RESOURCE_STATUS_APPROVED
    RejectionInProgress = strings.AIRLOCK_RESOURCE_STATUS_REJECTION_INPROGRESS
    Rejected = strings.AIRLOCK_RESOURCE_STATUS_REJECTED
    Cancelled = strings.AIRLOCK_RESOURCE_STATUS_CANCELLED

    Blocked = strings.AIRLOCK_RESOURCE_STATUS_BLOCKED
    BlockingInProgress = strings.AIRLOCK_RESOURCE_STATUS_BLOCKING_INPROGRESS
    Failed = strings.AIRLOCK_RESOURCE_STATUS_FAILED


class AirlockRequestType(str, Enum):
    Import = strings.AIRLOCK_REQUEST_TYPE_IMPORT
    Export = strings.AIRLOCK_REQUEST_TYPE_EXPORT


class AirlockReviewDecision(str, Enum):
    Approved = strings.AIRLOCK_RESOURCE_STATUS_APPROVAL_INPROGRESS
    Rejected = strings.AIRLOCK_RESOURCE_STATUS_REJECTION_INPROGRESS


class AirlockReview(AzureTREModel):
    """
    Airlock review
    """
    id: str = Field(title="Id", description="GUID identifying the review")
    reviewer: dict = {}
    dateCreated: float = 0
    reviewDecision: AirlockReviewDecision = Field("", title="Airlock review decision")
    decisionExplanation: str = Field(False, title="Explanation why the request was approved/rejected")


class AirlockRequestHistoryItem(AzureTREModel):
    """
    Resource History Item - to preserve history of resource properties
    """
    resourceVersion: int
    updatedWhen: float
    user: dict = {}
    properties: dict = {}


class AirlockRequest(AzureTREModel):
    """
    Airlock request
    """
    id: str = Field(title="Id", description="GUID identifying the resource")
    resourceVersion: int = 0
    user: dict = {}
    updatedWhen: float = 0
    history: List[AirlockRequestHistoryItem] = []
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    requestType: AirlockRequestType = Field("", title="Airlock request type")
    files: List[str] = Field([], title="Files of the request")
    businessJustification: str = Field("Business Justifications", title="Explanation that will be provided to the request reviewer")
    status = AirlockRequestStatus.Draft
    creationTime: float = Field(None, title="Creation time of the request")
    errorMessage: Optional[str] = Field(title="Present only if the request have failed, provides the reason of the failure.")
    reviews: Optional[List[AirlockReview]]
