from functools import lru_cache

from auth.token_validator import TokenValidator, TokenValidatorConfig
from core import config


def _jwks_uri() -> str:
    # Direct JWKS endpoint — PyJWKClient fetches this and parses it as a key set.
    return (
        f"{config.AAD_AUTHORITY_URL.rstrip('/')}"
        f"/{config.AAD_TENANT_ID}/discovery/v2.0/keys"
    )


def _issuer() -> str:
    return (
        f"{config.AAD_AUTHORITY_URL.rstrip('/')}"
        f"/{config.AAD_TENANT_ID}/v2.0"
    )


@lru_cache(maxsize=1)
def get_core_validator() -> TokenValidator:
    """Singleton :class:`TokenValidator` for the core TRE app registration."""
    return TokenValidator(
        TokenValidatorConfig(
            jwks_uri=_jwks_uri(),
            audience=config.API_AUDIENCE,
            issuer=_issuer(),
            is_workspace_token=False,
        )
    )


@lru_cache(maxsize=256)
def get_workspace_validator(client_id: str) -> TokenValidator:
    """Per-workspace :class:`TokenValidator`, cached by *client_id*.

    All workspace validators share the same JWKS URI so a single HTTP fetch
    serves all audiences; only the audience validation differs.
    """
    return TokenValidator(
        TokenValidatorConfig(
            jwks_uri=_jwks_uri(),
            audience=client_id,
            issuer=_issuer(),
            is_workspace_token=True,
        )
    )
