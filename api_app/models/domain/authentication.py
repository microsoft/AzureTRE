from collections import namedtuple
from typing import List, Optional
from pydantic import BaseModel, Field

RoleAssignment = namedtuple("RoleAssignment", "resource_id, role_id")


class User(BaseModel):
    id: str
    name: str
    email: Optional[str] = Field(default=None)
    roles: List[str] = Field(default_factory=list)
    roleAssignments: List[RoleAssignment] = Field(default_factory=list)
