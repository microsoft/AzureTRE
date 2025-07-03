from contextlib import asynccontextmanager
from core.config import MANAGED_IDENTITY_CLIENT_ID, AAD_TENANT_ID
from azure.core.credentials import TokenCredential

from azure.identity import (
    AzureCliCredential,
    ManagedIdentityCredential,
    ChainedTokenCredential,
)
from azure.identity.aio import (
    AzureCliCredential as AzureCliCredentialASync,
    ManagedIdentityCredential as ManagedIdentityCredentialASync,
    ChainedTokenCredential as ChainedTokenCredentialASync,
)


def get_credential() -> TokenCredential:
    if MANAGED_IDENTITY_CLIENT_ID:
        return ChainedTokenCredential(
            ManagedIdentityCredential(client_id=MANAGED_IDENTITY_CLIENT_ID)
        )
    else:
        return AzureCliCredential(tenant_id=AAD_TENANT_ID)


async def get_credential_async():
    return (
        ChainedTokenCredentialASync(
            ManagedIdentityCredentialASync(client_id=MANAGED_IDENTITY_CLIENT_ID)
        )
        if MANAGED_IDENTITY_CLIENT_ID
        else AzureCliCredentialASync(tenant_id=AAD_TENANT_ID)
    )


@asynccontextmanager
async def get_credential_async_context() -> TokenCredential:
    """
    Context manager which yields the default credentials.
    """
    credential = await get_credential_async()
    yield credential
    await credential.close()
