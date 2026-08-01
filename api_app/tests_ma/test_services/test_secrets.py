import pytest
from mock import AsyncMock, MagicMock, patch

from services.secrets import get_secret_value, is_secret_property, SecretRetrievalError
from azure.core.exceptions import ResourceNotFoundError


SECRET_ID = "https://kv-test.vault.azure.net/secrets/admin-password"


@pytest.mark.parametrize("property_name,expected", [
    ("admin_password_keyvault_secret_id", True),
    ("keyvault_secret_id", True),
    ("connection_string_keyvault_secret_id", True),
    ("display_name", False),
    ("password", False),
])
def test_is_secret_property(property_name, expected):
    assert is_secret_property(property_name) is expected


def _mock_secret_client(secret_value=None, get_secret_side_effect=None):
    secret_client = AsyncMock()
    if get_secret_side_effect is not None:
        secret_client.get_secret.side_effect = get_secret_side_effect
    else:
        secret = MagicMock()
        secret.value = secret_value
        secret_client.get_secret.return_value = secret
    secret_client.__aenter__.return_value = secret_client
    secret_client.__aexit__.return_value = None
    return secret_client


@patch("services.secrets.credentials.get_credential_async_context")
@patch("services.secrets.SecretClient")
@pytest.mark.asyncio
async def test_get_secret_value_returns_value(secret_client_cls, get_credential_context):
    get_credential_context.return_value.__aenter__.return_value = AsyncMock()
    secret_client_cls.return_value = _mock_secret_client(secret_value="super-secret")

    result = await get_secret_value(SECRET_ID)

    assert result == "super-secret"
    secret_client_cls.assert_called_once()
    assert secret_client_cls.call_args.kwargs["vault_url"] == "https://kv-test.vault.azure.net"


@pytest.mark.asyncio
async def test_get_secret_value_raises_on_invalid_identifier():
    with pytest.raises(SecretRetrievalError):
        await get_secret_value("not-a-valid-secret-id")


@pytest.mark.asyncio
async def test_get_secret_value_rejects_secret_outside_workspace():
    with pytest.raises(SecretRetrievalError):
        await get_secret_value(SECRET_ID, expected_keyvault_uri="https://other-kv.vault.azure.net/")


@patch("services.secrets.credentials.get_credential_async_context")
@patch("services.secrets.SecretClient")
@pytest.mark.asyncio
async def test_get_secret_value_raises_when_secret_not_found(secret_client_cls, get_credential_context):
    get_credential_context.return_value.__aenter__.return_value = AsyncMock()
    secret_client_cls.return_value = _mock_secret_client(get_secret_side_effect=ResourceNotFoundError("missing"))

    with pytest.raises(SecretRetrievalError):
        await get_secret_value(SECRET_ID)
