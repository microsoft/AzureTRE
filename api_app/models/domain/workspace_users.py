from typing import List
from pydantic import BaseModel, Field
from enum import Enum


class AssignableUser(BaseModel):
    id: str
    displayName: str
    userPrincipalName: str
    email: str = Field(default=None)


class AssignmentType(Enum):
    APP_ROLE = "ApplicationRole"
    GROUP = "Group"


class Role(BaseModel):
    id: str
    displayName: str

    def __eq__(self, other):
        if not isinstance(other, Role):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class AssignedUser(BaseModel):
    id: str
    displayName: str
    userPrincipalName: str
    email: str = Field(default=None)
    roles: List[Role] = Field(default_factory=list)
