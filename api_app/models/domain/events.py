from typing import Dict, Optional
from models.domain.azuretremodel import AzureTREModel


class AirlockNotificationData(AzureTREModel):
    request_id: str
    event_type: str
    event_value: str
    emails: Dict
    workspace_id: str
    short_workspace_id: str
    tre_url: str
    request_url: str


class StatusChangedData(AzureTREModel):
    request_id: str
    new_status: str
    previous_status: Optional[str]
    type: str
    workspace_id: str
