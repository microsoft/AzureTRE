from collections import namedtuple
from typing import List

from pydantic import BaseModel, Field


RoleAssignment = namedtuple("RoleAssignment", "resource_id, role_id")


class User(BaseModel):
    id: str
    name: str
    email: str = Field(None)
    roles: List[str] = Field([])
    roleAssignments: List[RoleAssignment] = Field([])


class AssignableUser(BaseModel):
    name: str
    email: str


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
