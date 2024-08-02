from pydantic import BaseModel, Field
from typing import List

class UsersInResponse(BaseModel):
    users: List[User] = Field(..., title="Users", description="List of users assigned to the workspace")

    class Config:
        schema_extra = {
            "example": {
                "users": [
                    {
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "roles": ["WorkspaceOwner", "WorkspaceResearcher"]
                    },
                    {
                        "name": "Jane Smith",
                        "email": "jane.smith@example.com",
                        "roles": ["WorkspaceResearcher"]
                    }
                ]
            }
        }
