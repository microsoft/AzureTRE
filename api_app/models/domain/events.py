from typing import List
from models.domain.azuretremodel import AzureTREModel


class AirlockNotificationData(AzureTREModel):
    request_id: str
    event_type: str
    event_value: str
    researchers_emails: List[str]
    owners_emails: List[str]
    workspace_id: str


class StatusChangedData(AzureTREModel):
    request_id: str
    status: str
    type: str
    workspace_id: str
