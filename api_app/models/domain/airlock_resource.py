from enum import Enum
from typing import List
from pydantic import Field
from models.domain.azuretremodel import AzureTREModel
from resources import strings


class AirlockRequestStatus(str, Enum):
    """
    Airlock Request status
    """
    Draft = strings.AIRLOCK_RESOURCE_STATUS_DRAFT
    Submitted = strings.AIRLOCK_RESOURCE_STATUS_SUBMITTED
    InReview = strings.AIRLOCK_RESOURCE_STATUS_INREVIEW
    Approved = strings.AIRLOCK_RESOURCE_STATUS_APPROVED
    Rejected = strings.AIRLOCK_RESOURCE_STATUS_REJECTED
    Cancelled = strings.AIRLOCK_RESOURCE_STATUS_CANCELLED
    Blocked = strings.AIRLOCK_RESOURCE_STATUS_BLOCKED


class AirlockResourceType(str, Enum):
    """
    Type of resource to create
    """
    AirlockRequest = strings.AIRLOCK_RESOURCE_TYPE_REQUEST
    # TBD Airlock review


class AirlockResourceHistoryItem(AzureTREModel):
    """
    Resource History Item - to preserve history of resource properties
    """
    resourceVersion: int
    updatedWhen: float
    user: dict = {}
    previousStatus: AirlockRequestStatus


class AirlockResource(AzureTREModel):
    """
    Resource request
    """
    id: str = Field(title="Id", description="GUID identifying the resource")
    resourceType: AirlockResourceType
    resourceVersion: int = 0
    user: dict = {}
    updatedWhen: float = 0
    history: List[AirlockResourceHistoryItem] = []
    status: AirlockRequestStatus
