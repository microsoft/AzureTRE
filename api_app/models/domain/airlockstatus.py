from pydantic import Field
from models.domain.azuretremodel import AzureTREModel


class AirLockStatus(AzureTREModel):
    """
    AirLockStatus model
    """
    id: str = Field(title="Id", description="GUID identifying the resource")
    status: int = Field(None, title="Airlock process status")
    message: str = Field("", title="Status message")
    createdBy: dict = {}
    createdWhen: float = Field("", title="POSIX Timestamp for when the operation was submitted")
    updatedBy:dict = {}
    updatedWhen: float = Field("", title="POSIX Timestamp for When the operation was updated")

