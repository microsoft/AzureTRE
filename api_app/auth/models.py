from enum import StrEnum
from typing import Optional, Tuple, Union

from pydantic import BaseModel, Field


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
    claim (the stable object identifier in Entra ID).  The model is frozen and
    ``roles`` is stored as a tuple so roles cannot be reassigned *or* mutated
    in place (e.g. ``roles.append(...)``) after creation.
    """

    id: str
    name: str
    email: Optional[str] = None
    roles: Tuple[str, ...] = Field(default_factory=tuple)
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
