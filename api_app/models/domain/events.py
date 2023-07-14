from typing import Dict, List, Optional

from models.domain.azuretremodel import AzureTREModel
from models.domain.airlock_request import AirlockFile, AirlockRequestStatus, AirlockRequestType


class AirlockNotificationUserData(AzureTREModel):
    name: str
    email: str


class AirlockNotificationRequestData(AzureTREModel):
    id: str
    created_when: float
    created_by: AirlockNotificationUserData
    updated_when: float
    updated_by: AirlockNotificationUserData
    request_type: AirlockRequestType
    files: List[AirlockFile]
    status: AirlockRequestStatus
    business_justification: str


class AirlockNotificationWorkspaceData(AzureTREModel):
    id: str
    display_name: str
    description: str


class AirlockNotificationData(AzureTREModel):
    event_type: str
    recipient_emails_by_role: Dict[str, List[str]]
    request: AirlockNotificationRequestData
    workspace: AirlockNotificationWorkspaceData


class StatusChangedData(AzureTREModel):
    request_id: str
    new_status: str
    previous_status: Optional[str]
    type: str
    workspace_id: str
