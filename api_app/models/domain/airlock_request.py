from typing import List
from enum import Enum
from pydantic import Field
from resources import strings
from models.domain.airlock_resource import AirlockRequestStatus, AirlockResource, AirlockResourceType


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
