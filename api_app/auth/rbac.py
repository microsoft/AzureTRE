from typing import Callable, Union

from fastapi import Depends, HTTPException, status

from auth.dependencies import get_authenticated_user, get_workspace_authenticated_user
from auth.models import AuthenticatedUser, TRERole, WorkspaceAccessRole
from resources import strings


def require_roles(*roles: Union[TRERole, WorkspaceAccessRole]) -> Callable:
    """Factory that returns a FastAPI dependency enforcing at least one of *roles*.

    The dependency validates the bearer token against the core app registration
    and raises HTTP 403 if the user does not hold at least one required role.
    """
    role_values = frozenset(r.value for r in roles)
    role_names = [r.value for r in roles]

    async def _check(
        user: AuthenticatedUser = Depends(get_authenticated_user),
    ) -> AuthenticatedUser:
        if not (set(user.roles) & role_values):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {role_names}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    return _check


def require_workspace_roles(*roles: Union[TRERole, WorkspaceAccessRole]) -> Callable:
    """Factory that returns a dependency enforcing workspace-scoped *roles*.

    TREAdmin users are always allowed regardless of workspace role.  For other
    users the token is validated against the workspace app registration and the
    role list is checked.

    Workspace context is resolved by pairing with
    ``Depends(get_workspace_by_id_from_path)`` on the route.
    """
    role_values = frozenset(r.value for r in roles)
    # TREAdmin can access any workspace endpoint
    allowed_values = role_values | {TRERole.Admin.value}
    role_names = [r.value for r in roles]

    async def _check(
        user: AuthenticatedUser = Depends(get_workspace_authenticated_user),
    ) -> AuthenticatedUser:
        if not (set(user.roles) & allowed_values):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {role_names}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    return _check


# ---------------------------------------------------------------------------
# Pre-built role checks — replace the module-level AzureADAuthorization
# singletons that previously lived in services/authentication.py.
# ---------------------------------------------------------------------------

require_tre_user = require_roles(TRERole.User)
require_tre_admin = require_roles(TRERole.Admin)
require_tre_user_or_admin = require_roles(TRERole.User, TRERole.Admin)
require_workspace_owner = require_workspace_roles(WorkspaceAccessRole.Owner)
require_workspace_researcher = require_workspace_roles(WorkspaceAccessRole.Researcher)
require_airlock_manager = require_workspace_roles(WorkspaceAccessRole.AirlockManager)
require_workspace_owner_or_researcher = require_workspace_roles(
    WorkspaceAccessRole.Owner, WorkspaceAccessRole.Researcher
)
require_workspace_owner_or_airlock_manager = require_workspace_roles(
    WorkspaceAccessRole.Owner, WorkspaceAccessRole.AirlockManager
)
require_workspace_owner_or_researcher_or_airlock_manager = require_workspace_roles(
    WorkspaceAccessRole.Owner,
    WorkspaceAccessRole.Researcher,
    WorkspaceAccessRole.AirlockManager,
)
