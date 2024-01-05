from contextlib import asynccontextmanager
from core.config import MANAGED_IDENTITY_CLIENT_ID, AAD_AUTHORITY_URL
from azure.core.credentials import TokenCredential
from urllib.parse import urlparse

from azure.identity import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    ChainedTokenCredential,
)
from azure.identity.aio import (
    DefaultAzureCredential as DefaultAzureCredentialASync,
    ManagedIdentityCredential as ManagedIdentityCredentialASync,
    ChainedTokenCredential as ChainedTokenCredentialASync,
)


def get_credential() -> TokenCredential:
    if MANAGED_IDENTITY_CLIENT_ID:
        return ChainedTokenCredential(
            ManagedIdentityCredential(client_id=MANAGED_IDENTITY_CLIENT_ID)
        )
    else:
        return DefaultAzureCredential(authority=urlparse(AAD_AUTHORITY_URL).netloc,
                                      exclude_shared_token_cache_credential=True,
                                      exclude_workload_identity_credential=True,
                                      exclude_developer_cli_credential=True,
                                      exclude_managed_identity_credential=True,
                                      exclude_powershell_credential=True
                                      )


async def get_credential_async():
    return (
        ChainedTokenCredentialASync(
            ManagedIdentityCredentialASync(client_id=MANAGED_IDENTITY_CLIENT_ID)
        )
        if MANAGED_IDENTITY_CLIENT_ID
        else DefaultAzureCredentialASync(authority=urlparse(AAD_AUTHORITY_URL).netloc,
                                         exclude_shared_token_cache_credential=True,
                                         exclude_workload_identity_credential=True,
                                         exclude_developer_cli_credential=True,
                                         exclude_managed_identity_credential=True,
                                         exclude_powershell_credential=True
                                         )
    )


@asynccontextmanager
async def get_credential_async_context() -> TokenCredential:
    """
    Context manager which yields the default credentials.
    """
    credential = await get_credential_async()
    yield credential
    await credential.close()
