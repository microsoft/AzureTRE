from pydantic import BaseModel, Field
from typing import List

from models.domain.authentication import User


class UsersInResponse(BaseModel):
    users: List[User] = Field(..., title="Users", description="List of users assigned to the workspace")

    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": 1,
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "roles": ["WorkspaceOwner", "WorkspaceResearcher"]
                    },
                    {
                        "id": 2,
                        "name": "Jane Smith",
                        "email": "jane.smith@example.com",
                        "roles": ["WorkspaceResearcher"]
                    }
                ]
            }
        }
