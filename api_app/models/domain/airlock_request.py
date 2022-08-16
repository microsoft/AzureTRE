from typing import List
from enum import Enum
from pydantic import Field
from pydantic.schema import Optional
from resources import strings
from models.domain.airlock_resource import AirlockResource, AirlockResourceType


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


class AirlockActions(str, Enum):
    Review = strings.AIRLOCK_ACTION_REVIEW
    Cancel = strings.AIRLOCK_ACTION_CANCEL
    Submit = strings.AIRLOCK_ACTION_SUBMIT


class AirlockRequest(AirlockResource):
    """
    Airlock request
    """
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    resourceType = AirlockResourceType.AirlockRequest
    requestType: AirlockRequestType = Field("", title="Airlock request type")
    files: List[str] = Field([], title="Files of the request")
    businessJustification: str = Field("Business Justifications", title="Explanation that will be provided to the request reviewer")
    status = AirlockRequestStatus.Draft
    creationTime: float = Field(None, title="Creation time of the request")
    errorMessage: Optional[str] = Field(title="Present only if the request have failed, provides the reason of the failure.")
