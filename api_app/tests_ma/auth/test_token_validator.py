"""Tests for auth.token_validator."""
import pytest
from unittest.mock import MagicMock, patch

from auth.exceptions import TokenExpired, TokenInvalid, TokenSignatureInvalid
from auth.models import AuthenticatedUser
from auth.token_validator import TokenValidator, TokenValidatorConfig


JWKS_URI = "https://login.microsoftonline.com/tenant/discovery/v2.0/keys"
AUDIENCE = "api://test-app"
ISSUER = "https://login.microsoftonline.com/tenant/v2.0"

SAMPLE_CLAIMS = {
    "oid": "user-object-id",
    "name": "Test User",
    "email": "test@example.com",
    "roles": ["TREAdmin", "TREUser"],
}


def _make_validator(mock_jwks_client: MagicMock) -> TokenValidator:
    config = TokenValidatorConfig(
        jwks_uri=JWKS_URI,
        audience=AUDIENCE,
        issuer=ISSUER,
    )
    with patch("auth.token_validator.PyJWKClient", return_value=mock_jwks_client):
        return TokenValidator(config)


def _make_mock_jwks_client(signing_key: MagicMock) -> MagicMock:
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = signing_key
    return client


class TestTokenValidatorValidate:
    def test_returns_authenticated_user_on_valid_token(self):
        import jwt as pyjwt

        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch("auth.token_validator.jwt.decode", return_value=SAMPLE_CLAIMS):
            result = validator.validate("valid.jwt.token")

        assert isinstance(result, AuthenticatedUser)
        assert result.id == "user-object-id"
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        assert "TREAdmin" in result.roles

    def test_frozen_user_cannot_be_mutated(self):
        import jwt as pyjwt

        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch("auth.token_validator.jwt.decode", return_value=SAMPLE_CLAIMS):
            user = validator.validate("valid.jwt.token")

        with pytest.raises(TypeError):
            user.roles = []  # type: ignore[misc]

    def test_raises_token_expired_on_expired_signature(self):
        import jwt as pyjwt

        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch(
            "auth.token_validator.jwt.decode",
            side_effect=pyjwt.ExpiredSignatureError("expired"),
        ):
            with pytest.raises(TokenExpired):
                validator.validate("expired.jwt.token")

    def test_raises_token_invalid_on_generic_jwt_error(self):
        import jwt as pyjwt

        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch(
            "auth.token_validator.jwt.decode",
            side_effect=pyjwt.InvalidTokenError("bad token"),
        ):
            with pytest.raises(TokenInvalid):
                validator.validate("bad.jwt.token")

    def test_raises_token_invalid_when_signing_key_unavailable(self):
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.side_effect = Exception("key fetch failed")
        validator = _make_validator(mock_client)

        with pytest.raises(TokenInvalid, match="Cannot obtain signing key"):
            validator.validate("any.jwt.token")

    def test_email_falls_back_to_preferred_username(self):
        claims_no_email = {
            "oid": "uid",
            "name": "User",
            "preferred_username": "user@tenant.com",
            "roles": [],
        }
        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch("auth.token_validator.jwt.decode", return_value=claims_no_email):
            result = validator.validate("token")

        assert result.email == "user@tenant.com"

    def test_roles_default_to_empty_list(self):
        claims_no_roles = {"oid": "uid", "name": "User"}
        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch("auth.token_validator.jwt.decode", return_value=claims_no_roles):
            result = validator.validate("token")

        assert result.roles == []

    def test_raises_token_signature_invalid_on_invalid_signature(self):
        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch(
            "auth.token_validator.jwt.decode",
            side_effect=pytest.importorskip("jwt").InvalidSignatureError("bad sig"),
        ):
            with pytest.raises(TokenSignatureInvalid):
                validator.validate("tampered.jwt.token")

    def test_raises_token_invalid_on_audience_mismatch(self):
        import jwt as pyjwt

        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch(
            "auth.token_validator.jwt.decode",
            side_effect=pyjwt.InvalidAudienceError("wrong audience"),
        ):
            with pytest.raises(TokenInvalid):
                validator.validate("wrong-audience.jwt.token")

    def test_raises_token_invalid_on_issuer_mismatch(self):
        import jwt as pyjwt

        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch(
            "auth.token_validator.jwt.decode",
            side_effect=pyjwt.InvalidIssuerError("wrong issuer"),
        ):
            with pytest.raises(TokenInvalid):
                validator.validate("wrong-issuer.jwt.token")

    def test_raises_token_invalid_on_algorithm_confusion(self):
        """Tokens using an unexpected algorithm (e.g. 'none' or HS256) must be rejected."""
        import jwt as pyjwt

        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch(
            "auth.token_validator.jwt.decode",
            side_effect=pyjwt.InvalidAlgorithmError("algorithm not allowed"),
        ):
            with pytest.raises(TokenInvalid):
                validator.validate("alg-confusion.jwt.token")

    def test_decode_is_called_with_rs256_algorithm_only(self):
        """jwt.decode must always be called with algorithms=['RS256'] and no others."""
        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch("auth.token_validator.jwt.decode", return_value=SAMPLE_CLAIMS) as mock_decode:
            validator.validate("valid.jwt.token")

        call_kwargs = mock_decode.call_args
        algorithms_arg = call_kwargs.kwargs.get("algorithms")
        assert algorithms_arg == ["RS256"], (
            f"Expected algorithms=['RS256'] only, got {algorithms_arg!r}"
        )

    def test_raises_token_invalid_on_missing_oid_claim(self):
        """A token whose payload lacks the 'oid' claim must raise TokenInvalid, not KeyError."""
        claims_without_oid = {"name": "User", "email": "u@example.com", "roles": []}
        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        validator = _make_validator(mock_client)

        with patch("auth.token_validator.jwt.decode", return_value=claims_without_oid):
            with pytest.raises(TokenInvalid, match="oid"):
                validator.validate("no-oid.jwt.token")

    def test_is_workspace_token_flag_set_from_config(self):
        signing_key = MagicMock()
        mock_client = _make_mock_jwks_client(signing_key)
        config = TokenValidatorConfig(
            jwks_uri=JWKS_URI,
            audience="ws-client-id",
            issuer=ISSUER,
            is_workspace_token=True,
        )
        with patch("auth.token_validator.PyJWKClient", return_value=mock_client):
            validator = TokenValidator(config)

        with patch("auth.token_validator.jwt.decode", return_value=SAMPLE_CLAIMS):
            result = validator.validate("token")

        assert result.is_workspace_token is True
