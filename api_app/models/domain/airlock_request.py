from typing import List
from enum import Enum
from pydantic import Field
from resources import strings
from models.domain.airlock_resource import AirlockResource, AirlockResourceType


class AirlockRequestStatus(str, Enum):
    """
    Airlock Resource status
    """
    Draft = strings.AIRLOCK_RESOURCE_STATUS_DRAFT
    Submitted = strings.AIRLOCK_RESOURCE_STATUS_SUBMITTED
    InScan = strings.AIRLOCK_RESOURCE_STATUS_INSCAN
    InReview = strings.AIRLOCK_RESOURCE_STATUS_INREVIEW
    Approved = strings.AIRLOCK_RESOURCE_STATUS_APPROVED
    Rejected = strings.AIRLOCK_RESOURCE_STATUS_REJECTED
    Cancelled = strings.AIRLOCK_RESOURCE_STATUS_CANCELLED
    Blocked = strings.AIRLOCK_RESOURCE_STATUS_BLOCKED
    Ready = strings.AIRLOCK_RESOURCE_STATUS_READY
    Declined = strings.AIRLOCK_RESOURCE_STATUS_DECLINED
    Failed = strings.AIRLOCK_RESOURCE_STATUS_FAILED


class AirlockRequestType(str, Enum):
    Import = strings.AIRLOCK_REQUEST_TYPE_IMPORT
    Export = strings.AIRLOCK_REQUEST_TYPE_EXPORT


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
