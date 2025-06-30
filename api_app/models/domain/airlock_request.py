from enum import StrEnum
from typing import List, Dict, Optional

from models.domain.azuretremodel import AzureTREModel
from pydantic import Field, validator
from resources import strings


class AirlockRequestStatus(StrEnum):
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
    Revoked = strings.AIRLOCK_RESOURCE_STATUS_REVOKED


class AirlockRequestType(StrEnum):
    Import = strings.AIRLOCK_REQUEST_TYPE_IMPORT
    Export = strings.AIRLOCK_REQUEST_TYPE_EXPORT


class AirlockActions(StrEnum):
    Review = strings.AIRLOCK_ACTION_REVIEW
    Cancel = strings.AIRLOCK_ACTION_CANCEL
    Submit = strings.AIRLOCK_ACTION_SUBMIT
    Revoke = strings.AIRLOCK_ACTION_REVOKE


class AirlockFile(AzureTREModel):
    name: str = Field(title="name", description="name of the file")
    size: float = Field(title="size", description="size of the file in bytes")


class AirlockReviewDecision(StrEnum):
    Approved = strings.AIRLOCK_REVIEW_DECISION_APPROVED
    Rejected = strings.AIRLOCK_REVIEW_DECISION_REJECTED
    Revoked = strings.AIRLOCK_REVIEW_DECISION_REVOKED


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
    updatedBy: dict = {}
    properties: dict = {}


class AirlockReviewUserResource(AzureTREModel):
    """
    User resource created for Airlock Review
    """
    workspaceId: str = Field(title="Workspace ID")
    workspaceServiceId: str = Field(title="Workspace Service ID")
    userResourceId: str = Field(title="User Resource ID")


class AirlockRequest(AzureTREModel):
    """
    Airlock request
    """
    id: str = Field(title="Id", description="GUID identifying the resource")
    resourceVersion: int = 0
    createdBy: dict = {}
    createdWhen: float = Field(None, title="Creation time of the request")
    updatedBy: dict = {}
    updatedWhen: float = 0
    history: List[AirlockRequestHistoryItem] = []
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    type: AirlockRequestType = Field("", title="Airlock request type")
    files: List[AirlockFile] = Field([], title="Files of the request")
    title: str = Field("Airlock Request", title="Brief title for the request")
    businessJustification: str = Field("Business Justification", title="Explanation that will be provided to the request reviewer")
    status = AirlockRequestStatus.Draft
    statusMessage: Optional[str] = Field(title="Optional - contains additional information about the current status.")
    reviews: Optional[List[AirlockReview]]
    etag: Optional[str] = Field(title="_etag", alias="_etag")
    reviewUserResources: Dict[str, AirlockReviewUserResource] = Field({}, title="User resources created for Airlock Reviews")

    # SQL API CosmosDB saves ETag as an escaped string: https://github.com/microsoft/AzureTRE/issues/1931
    @validator("etag", pre=True)
    def parse_etag_to_remove_escaped_quotes(cls, value):
        if value:
            return value.replace('\"', '')
