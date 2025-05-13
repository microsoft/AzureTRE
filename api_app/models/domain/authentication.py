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
