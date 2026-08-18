from contextlib import asynccontextmanager
from core.config import MANAGED_IDENTITY_CLIENT_ID, AAD_AUTHORITY_URL
from azure.core.credentials import TokenCredential
from urllib.parse import urlparse

from azure.identity import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    ChainedTokenCredential,
    ClientAssertionCredential,
)
from azure.identity.aio import (
    DefaultAzureCredential as DefaultAzureCredentialASync,
    ManagedIdentityCredential as ManagedIdentityCredentialASync,
    ChainedTokenCredential as ChainedTokenCredentialASync,
)

# Audience used when exchanging the core API managed identity token for the
# per-workspace airlock SAS signer app token (workload identity federation).
TOKEN_EXCHANGE_AUDIENCE = "api://AzureADTokenExchange/.default"  # nosec B105 - token exchange audience, not a secret


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


def get_airlock_signer_credential(signer_client_id: str, tenant_id: str) -> TokenCredential:
    """Return a credential that authenticates as the per-workspace airlock SAS signer
    app registration, via workload identity federation from the core API managed identity.

    User-delegation SAS are signed by (skoid =) whichever identity requests the user
    delegation key. Signing as the per-workspace signer makes the per-workspace ABAC
    condition on the shared global airlock storage account enforceable and prevents a
    SAS leaked from one workspace being replayed from another. Requires the core API
    managed identity to be configured as a federated identity credential on the signer.
    """
    managed_identity = ManagedIdentityCredential(client_id=MANAGED_IDENTITY_CLIENT_ID)

    def _get_managed_identity_assertion() -> str:
        return managed_identity.get_token(TOKEN_EXCHANGE_AUDIENCE).token

    return ClientAssertionCredential(
        tenant_id=tenant_id,
        client_id=signer_client_id,
        func=_get_managed_identity_assertion,
        authority=urlparse(AAD_AUTHORITY_URL).netloc,
    )
