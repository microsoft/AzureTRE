from pydantic import Field
from pydantic.types import UUID4
from models.domain.azuretremodel import AzureTREModel


class EventGridMessageData(AzureTREModel):
    completed_step: str = Field(title="", description="")
    new_status: str = Field(title="", description="")
    request_id: str = Field(title="", description="")


class StepResultStatusUpdateMessage(AzureTREModel):
    """
    Model for service bus message flowing back to API to update status in DB
    """
    id: UUID4 = Field(title="", description="")
    subject: str = Field(title="", description="")
    data: EventGridMessageData = Field(title="", description="")
    eventType: str = Field(title="", description="")
    eventTime: str = Field(title="", description="")
    topic: str = Field(title="", description="")
