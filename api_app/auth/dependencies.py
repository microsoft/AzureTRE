from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.exceptions import AuthError, TokenExpired, TokenInvalid, TokenSignatureInvalid
from auth.models import AuthenticatedUser
from auth.registry import get_core_validator, get_workspace_validator
from models.domain.workspace import Workspace
from resources import strings
from services.logging import logger

_bearer = HTTPBearer(auto_error=True)


def _to_http_exception(exc: AuthError) -> HTTPException:
    if isinstance(exc, TokenExpired):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=strings.EXPIRED_SIGNATURE,
        )
    if isinstance(exc, TokenSignatureInvalid):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=strings.INVALID_SIGNATURE,
        )
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=strings.INVALID_TOKEN,
    )


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthenticatedUser:
    """Validate the bearer token against the core TRE app registration.

    Returns an immutable :class:`AuthenticatedUser` or raises HTTP 401.
    """
    try:
        return get_core_validator().validate(credentials.credentials)
    except AuthError as exc:
        logger.debug("Core token validation failed: %s", exc)
        raise _to_http_exception(exc)


async def get_workspace_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    workspace: Workspace = Depends(lambda: None),
) -> AuthenticatedUser:
    """Validate the bearer token for a workspace-scoped request.

    Tries the workspace app registration first.  If that audience validation
    fails (but not on expiry or signature errors), falls back to the core app
    registration so that TREAdmin users can always reach workspace endpoints.

    The *workspace* parameter should be provided via
    ``Depends(get_workspace_by_id_from_path)`` when wiring routes.
    """
    token = credentials.credentials

    if workspace is not None:
        client_id = workspace.properties.get("client_id", "")
        if client_id:
            try:
                return get_workspace_validator(client_id).validate(token)
            except (TokenExpired, TokenSignatureInvalid) as exc:
                # Hard failures — the token IS for this workspace but is bad.
                logger.debug("Workspace token hard failure: %s", exc)
                raise _to_http_exception(exc)
            except TokenInvalid as exc:
                # Wrong audience — fall through to core validator.
                logger.debug(
                    "Workspace token invalid (likely wrong audience), "
                    "trying core validator: %s",
                    exc,
                )

    # Fall back to core app registration (allows TREAdmin access).
    try:
        return get_core_validator().validate(token)
    except AuthError as exc:
        logger.debug("Core token validation failed: %s", exc)
        raise _to_http_exception(exc)
