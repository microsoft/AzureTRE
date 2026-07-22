from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.exceptions import AuthError, TokenExpired, TokenSignatureInvalid
from auth.models import AuthenticatedUser
from auth.registry import get_core_validator
from resources import strings
from services.logging import logger

_bearer = HTTPBearer(auto_error=True)


def _to_http_exception(exc: AuthError) -> HTTPException:
    if isinstance(exc, TokenExpired):
        detail = strings.EXPIRED_SIGNATURE
    elif isinstance(exc, TokenSignatureInvalid):
        detail = strings.INVALID_SIGNATURE
    else:
        detail = strings.INVALID_TOKEN
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
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
