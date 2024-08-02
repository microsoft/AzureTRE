from pydantic import BaseModel, Field
from typing import List

class User(BaseModel):
    name: str = Field(..., title="Name", description="The name of the user")
    email: str = Field(..., title="Email", description="The email of the user")
    roles: List[str] = Field(..., title="Roles", description="The roles assigned to the user")
