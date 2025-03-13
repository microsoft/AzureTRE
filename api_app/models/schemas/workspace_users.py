from typing import List
from pydantic import BaseModel, Field


class UserRoleAssignmentRequest(BaseModel):
    role_id: str = Field(title="Role Id", description="Role to assign users to")
    user_ids: List[str] = Field(default_factory=list, title="List of User Ids", description="List of User Ids to assign the role to")

    class Config:
        schema_extra = {
            "example": {
                "role_id": "1234",
                "user_ids": ["1", "2"]
            }
        }
