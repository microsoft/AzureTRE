from typing import Callable, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from auth.dependencies import require_bearer_credentials, _to_http_exception, get_authenticated_user
from auth.exceptions import AuthError, TokenExpired, TokenSignatureInvalid, TokenInvalid
from auth.models import AuthenticatedUser, TRERole, WorkspaceAccessRole
from auth.registry import get_core_validator, get_workspace_validator
from models.domain.workspace import Workspace
from resources import strings
from services.logging import logger

# Workspace dependency from API layer — needed to resolve workspace app registration
# for audience-aware token validation on workspace-scoped routes.
from api.dependencies.workspaces import get_workspace_by_id_from_path


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

    _check._role_names = role_names
    return _check


def require_workspace_roles(
    *roles: Union[TRERole, WorkspaceAccessRole],
    allow_tre_admin: bool = False,
) -> Callable:
    """Factory that returns a dependency enforcing workspace-scoped *roles*.

    Validates the bearer token against the workspace app registration first
    (audience-aware). A token carrying one of the required workspace *roles* is
    accepted.

    ``allow_tre_admin`` controls whether a TREAdmin — who authenticates with a
    *core* token (wrong audience for the workspace app registration) — may also
    reach the endpoint. When ``True``, a wrong-audience token falls back to the
    core app registration and is accepted **only** if it is a valid TREAdmin
    token. When ``False`` (the default), no core fallback occurs and any token
    that is not valid for the workspace audience is rejected with 401 — this
    preserves the separation between platform administration and workspace
    access.

    The workspace is resolved from the URL path (``workspace_id`` path
    parameter) so this factory should only be used on routes whose path
    includes ``{workspace_id}``.
    """
    role_values = frozenset(r.value for r in roles)
    allowed_values = role_values | ({TRERole.Admin.value} if allow_tre_admin else frozenset())
    role_names = [r.value for r in roles]

    async def _check(
        credentials: HTTPAuthorizationCredentials = Depends(require_bearer_credentials),
        workspace: Workspace = Depends(get_workspace_by_id_from_path),
    ) -> AuthenticatedUser:
        token = credentials.credentials

        # Try workspace app registration first (audience-aware validation).
        client_id = workspace.properties.get("client_id", "")
        if client_id:
            try:
                user = get_workspace_validator(client_id).validate(token)
                # Token is valid for this workspace — role check is final.
                if not (set(user.roles) & allowed_values):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"{strings.ACCESS_USER_DOES_NOT_HAVE_REQUIRED_ROLE}: {role_names}",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                return user
            except (TokenExpired, TokenSignatureInvalid) as exc:
                raise _to_http_exception(exc)
            except TokenInvalid:
                # Wrong audience — only a TREAdmin core token may proceed, and
                # only when this endpoint opts in via allow_tre_admin.
                logger.debug(
                    "Workspace token invalid (likely wrong audience), trying core validator"
                )

        # Endpoints that do not permit TREAdmin get no cross-audience fallback:
        # a token that is not valid for the workspace audience is rejected.
        if not allow_tre_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=strings.INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fall back to core app registration. A core token is only accepted
        # here for TREAdmin; any other valid core token is treated as invalid
        # for this workspace resource.
        try:
            user = get_core_validator().validate(token)
        except AuthError as exc:
            raise _to_http_exception(exc)

        if not user.is_tre_admin():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=strings.INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    _check._role_names = role_names
    return _check


# ---------------------------------------------------------------------------
# Pre-built role checks — replace the module-level AzureADAuthorization
# singletons that previously lived in services/authentication.py.
# ---------------------------------------------------------------------------

require_tre_user = require_roles(TRERole.User)
require_tre_admin = require_roles(TRERole.Admin)
require_tre_user_or_admin = require_roles(TRERole.User, TRERole.Admin)

# Workspace-scoped checks WITHOUT TREAdmin access (workspace roles only).
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

# Workspace-scoped checks that ALSO permit TREAdmin (mirror the old
# ``..._or_tre_admin`` dependencies).
require_workspace_owner_or_tre_admin = require_workspace_roles(
    WorkspaceAccessRole.Owner, allow_tre_admin=True
)
require_workspace_owner_or_researcher_or_tre_admin = require_workspace_roles(
    WorkspaceAccessRole.Owner, WorkspaceAccessRole.Researcher, allow_tre_admin=True
)
require_workspace_owner_or_researcher_or_airlock_manager_or_tre_admin = require_workspace_roles(
    WorkspaceAccessRole.Owner,
    WorkspaceAccessRole.Researcher,
    WorkspaceAccessRole.AirlockManager,
    allow_tre_admin=True,
)
