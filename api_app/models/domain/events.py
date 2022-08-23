from typing import Dict
from models.domain.azuretremodel import AzureTREModel


class AirlockNotificationData(AzureTREModel):
    request_id: str
    event_type: str
    event_value: str
    emails: Dict
    workspace_id: str


class StatusChangedData(AzureTREModel):
    request_id: str
    status: str
    type: str
    workspace_id: str
