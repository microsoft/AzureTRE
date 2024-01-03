from unittest.mock import MagicMock, patch
from urllib.parse import urlparse
import pytest

from azure.identity.aio import (
    DefaultAzureCredential as DefaultAzureCredentialASync,
    ManagedIdentityCredential as ManagedIdentityCredentialASync,
    ChainedTokenCredential as ChainedTokenCredentialASync,
)

from core.credentials import get_credential_async

pytestmark = pytest.mark.asyncio


@patch("core.credentials.MANAGED_IDENTITY_CLIENT_ID", "mocked_client_id")
async def test_get_credential_async_with_managed_identity_client_id():
    credential = await get_credential_async()

    assert isinstance(credential.credentials[0], ManagedIdentityCredentialASync)


async def test_get_credential_async_without_managed_identity_client_id():
    credential = await get_credential_async()

    assert isinstance(credential, DefaultAzureCredentialASync)
