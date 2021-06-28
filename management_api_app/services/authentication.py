from typing import List

from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    name: str
    email: str
    roles: List[str] = Field([])
    roleAssignments: dict = Field({})
