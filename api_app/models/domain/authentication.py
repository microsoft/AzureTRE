from collections import namedtuple
from typing import List
from pydantic import BaseModel, Field
from enum import Enum

RoleAssignment = namedtuple("RoleAssignment", "resource_id, role_id")

class User(BaseModel):
    id: str
    name: str
    email: str = Field(None)
    roles: List[str] = Field([])
    roleAssignments: List[RoleAssignment] = Field([])

class Role(BaseModel):
    id: str
    value: str
    isEnabled: bool
    email: str = Field(None)
    allowedMemberTypes: List[str] = Field([])
    description: str
    displayName: str
    origin: str
    roleAssignments: List[RoleAssignment] = Field([])

class AssignableUser(BaseModel):
    id: str
    displayName: str
    userPrincipalName: str

class AssignmentType(Enum):
    APP_ROLE = "ApplicationRole"
    GROUP = "Group"

class AssignedRole(BaseModel):
    id: str
    displayName: str
    type: AssignmentType

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

class AssignedUser(BaseModel):
    id: str
    displayName: str
    userPrincipalName: str
    roles: List[AssignedRole] = Field([])
    


