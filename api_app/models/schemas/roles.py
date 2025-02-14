from pydantic import BaseModel, Field
from typing import List

from models.domain.authentication import Role

class RolesInResponse(BaseModel):
    roles: List[Role] = Field(..., title="Roles", description="List of roles in a workspace")
