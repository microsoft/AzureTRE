from enum import Enum
from typing import List
from uuid import UUID
from models.domain.azuretremodel import AzureTREModel


class ResourceAssignmentPermission(Enum):
    WorkspaceWrite = 1
    WorkspaceRead = 2
    WorkspaceDelete = 3
    WorkspaceCreateService = 4
    WorkspaceUserRead = 5
    WorkspaceUserManage = 6
    ServiceRead = 7
    ServiceWrite = 8
    ServiceDelete = 9


class ResourceAssignment(AzureTREModel):
    id: str
    userId: str
    resourceId: UUID
    permissions: List[ResourceAssignmentPermission]
