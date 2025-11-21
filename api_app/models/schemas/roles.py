from pydantic import BaseModel, Field
from typing import List
from models.domain.workspace_users import Role


class RolesInResponse(BaseModel):
    roles: List[Role] = Field(..., title="Roles", description="List of roles in a workspace")
