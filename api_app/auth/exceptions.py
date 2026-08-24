class AuthError(Exception):
    """Base class for all authentication and authorisation errors."""


class TokenExpired(AuthError):
    """The JWT has passed its expiry time."""


class TokenSignatureInvalid(AuthError):
    """The JWT signature does not match the signing key."""


class TokenInvalid(AuthError):
    """The JWT is structurally invalid or fails claims validation."""


class InsufficientPermissions(AuthError):
    """The authenticated user does not hold the required role."""


class WorkspaceNotFound(AuthError):
    """The requested workspace could not be found."""
