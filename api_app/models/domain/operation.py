from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

from pydantic import Field
from pydantic.types import UUID4

from models.domain.azuretremodel import AzureTREModel
from models.domain.resource import Output
from resources import strings

class Status(str, Enum):
    """
    Operation status
    """
    Failed = strings.RESOURCE_STATUS_FAILED
    Deleted = strings.RESOURCE_STATUS_DELETED
    Deployed = strings.RESOURCE_STATUS_DEPLOYED
    Deleting = strings.RESOURCE_STATUS_DELETING
    Deploying = strings.RESOURCE_STATUS_DEPLOYING
    NotDeployed = strings.RESOURCE_STATUS_NOT_DEPLOYED
    DeletingFailed = strings.RESOURCE_STATUS_DELETING_FAILED

class Operation(AzureTREModel):
    id: str = Field(title="Id", description="GUID identifying the operation")
    resourceId: str = Field(title="resourceId", description="GUID identifying the resource")
    resourceVersion: int = Field(0, title="resourceVersion", description="Version if the resource this operation relates to")
    status: Status = Field(Status.NotDeployed, title="Operation status")
    message: str = Field("", title="Additional operation status information")
    createdWhen: datetime = Field("", title="When the operation was submitted")
    updatedWhen: datetime = Field("", title="When the operation was updated")

class DeploymentStatusUpdateMessage(AzureTREModel):
    operationId: str = Field(title="", description="")
    id: UUID4 = Field(title="", description="")
    status: Status = Field(title="", description="")
    message: str = Field(title="", description="")
    outputs: List[Output] = Field(title="", description="", default=[])
