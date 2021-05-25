from typing import List
from uuid import UUID
from enum import Enum
from models.domain.azuretremodel import AzureTREModel


class OperationType(Enum):
    Create = 1
    Update = 2
    Delete = 3


class OperationStatus(Enum):
    Pending = 1
    Processing = 2
    Succeeded = 3
    Failed = 4


class OperationEvent:
    timeStamp: str
    message: str


class Operation(AzureTREModel):
    id: UUID
    operationType: OperationType
    status: OperationStatus
    resourceId: UUID
    resourceVersion: str
    createdAt: str
    lastUpdatedAt: str
    events: List[OperationEvent]
