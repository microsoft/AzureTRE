from dataclasses import dataclass
from typing import Optional

import jwt
from jwt import PyJWKClient

from auth.exceptions import TokenExpired, TokenInvalid, TokenSignatureInvalid
from auth.models import AuthenticatedUser


@dataclass(frozen=True)
class TokenValidatorConfig:
    jwks_uri: str
    audience: str
    issuer: str
    is_workspace_token: bool = False


class TokenValidator:
    """Single responsibility: validate a JWT and return a typed user.

    Uses :class:`jwt.PyJWKClient` which handles JWKS caching and key rotation
    automatically — keys removed from the JWKS endpoint are evicted from the
    cache, preventing unbounded growth.

    A ``jwks_client`` may be supplied so that multiple validators sharing the
    same JWKS endpoint (e.g. all per-workspace validators) reuse a single
    client and its key cache, avoiding redundant HTTP fetches.
    """

    def __init__(
        self,
        config: TokenValidatorConfig,
        jwks_client: Optional[PyJWKClient] = None,
    ) -> None:
        self._config = config
        self._jwks_client = jwks_client or PyJWKClient(
            config.jwks_uri, cache_keys=True, lifespan=300
        )

    def validate(self, token: str) -> AuthenticatedUser:
        """Validate *token* and return an :class:`AuthenticatedUser`.

        No silent exceptions — every failure mode raises a typed error.

        Raises:
            TokenExpired: token has passed its expiry time.
            TokenSignatureInvalid: signature cannot be verified.
            TokenInvalid: any other validation failure.
        """
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        except Exception as exc:
            raise TokenInvalid("Cannot obtain signing key") from exc

        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._config.audience,
                issuer=self._config.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    # Reject tokens that omit these claims entirely — PyJWT only
                    # validates a claim's value when present, so without this a
                    # token lacking `exp` would never be considered expired.
                    "require": ["exp", "iss", "aud"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpired("Token expired") from exc
        except jwt.InvalidSignatureError as exc:
            raise TokenSignatureInvalid("Token signature invalid") from exc
        except jwt.InvalidTokenError as exc:
            raise TokenInvalid(f"Token invalid: {exc}") from exc

        from pydantic import ValidationError

        try:
            return AuthenticatedUser(
                id=claims["oid"],
                name=claims.get("name", ""),
                email=claims.get("email") or claims.get("preferred_username"),
                roles=claims.get("roles") or [],
                audience=self._config.audience,
                is_workspace_token=self._config.is_workspace_token,
            )
        except KeyError as exc:
            raise TokenInvalid("Token is missing required claim: oid") from exc
        except (ValidationError, TypeError) as exc:
            raise TokenInvalid("Token claims are invalid") from exc
