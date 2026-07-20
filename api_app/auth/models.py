from enum import StrEnum
from typing import List, Optional, Union

from pydantic import BaseModel


class TRERole(StrEnum):
    Admin = "TREAdmin"
    User = "TREUser"
    AirlockAutomation = "TREAirlockAutomation"


class WorkspaceAccessRole(StrEnum):
    Owner = "WorkspaceOwner"
    Researcher = "WorkspaceResearcher"
    AirlockManager = "AirlockManager"


class AuthenticatedUser(BaseModel):
    """Immutable, validated user derived from a JWT.

    Fields map directly to standard JWT claims; ``id`` holds the ``oid``
    claim (the stable object identifier in Entra ID).  The model is frozen so
    roles cannot be escalated after creation.
    """

    id: str
    name: str
    email: Optional[str] = None
    roles: List[str] = []
    audience: str = ""
    is_workspace_token: bool = False

    class Config:
        frozen = True

    def has_any_role(self, *roles: Union[TRERole, WorkspaceAccessRole]) -> bool:
        """Return *True* if the user holds at least one of *roles*."""
        role_values = {r.value for r in roles}
        return bool(role_values & set(self.roles))

    def is_tre_admin(self) -> bool:
        return TRERole.Admin.value in self.roles
