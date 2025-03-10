from pydantic import BaseModel, Field
from typing import List

from models.domain.workspace_users import AssignedUser, AssignableUser


class UsersInResponse(BaseModel):
    users: List[AssignedUser] = Field(..., title="Users", description="List of users assigned to the workspace")

    class Config:
        schema_extra = {
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


class AssignableUsersInResponse(BaseModel):
    assignable_users: List[AssignableUser] = Field(..., title="Assignable Users", description="List of users assignable to a workspace")


class WorkspaceUserOperationResponse(BaseModel):
    user_ids: List[str] = Field(..., title="User IDs", description="List of user IDs")
    role_id: str = Field(..., title="Role ID", description="Role ID")
