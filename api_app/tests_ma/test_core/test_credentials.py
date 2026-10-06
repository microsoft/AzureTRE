from unittest.mock import AsyncMock, patch
import pytest

from azure.identity.aio import (
    DefaultAzureCredential as DefaultAzureCredentialASync,
    ManagedIdentityCredential as ManagedIdentityCredentialASync
)

from core.credentials import get_credential_async, get_credential_async_context

pytestmark = pytest.mark.asyncio


@patch("core.credentials.MANAGED_IDENTITY_CLIENT_ID", "mocked_client_id")
async def test_get_credential_async_with_managed_identity_client_id():
    credential = await get_credential_async()

    assert isinstance(credential.credentials[0], ManagedIdentityCredentialASync)


async def test_get_credential_async_without_managed_identity_client_id():
    credential = await get_credential_async()

    assert isinstance(credential, DefaultAzureCredentialASync)


async def test_get_credential_async_context_closes_credential():
    mock_credential = AsyncMock()
    with patch("core.credentials.get_credential_async", return_value=mock_credential):
        async with get_credential_async_context() as cred:
            assert cred == mock_credential

    mock_credential.close.assert_awaited_once()


async def test_get_credential_async_context_closes_credential_on_exception():
    mock_credential = AsyncMock()
    with patch("core.credentials.get_credential_async", return_value=mock_credential):
        with pytest.raises(RuntimeError, match="Test Error"):
            async with get_credential_async_context():
                raise RuntimeError("Test Error")

    mock_credential.close.assert_awaited_once()
