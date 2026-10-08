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

# Workload-identity token-exchange audience. Sovereign clouds use their own audience,
# and it must match the audience on the workspace signer's federated credential.


def _token_exchange_audience() -> str:
    host = urlparse(AAD_AUTHORITY_URL).netloc.lower()
    if host.endswith(".us"):
        return "api://AzureADTokenExchangeUSGov/.default"
    if host.endswith(".cn"):
        return "api://AzureADTokenExchangeChina/.default"
    return "api://AzureADTokenExchange/.default"


TOKEN_EXCHANGE_AUDIENCE = _token_exchange_audience()  # nosec B105 - token exchange audience, not a secret


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
    try:
        yield credential
    finally:
        await credential.close()


def get_airlock_signer_credential(signer_client_id: str, tenant_id: str) -> TokenCredential:
    """Authenticate as a workspace's federated airlock signer."""
    managed_identity = ManagedIdentityCredential(client_id=MANAGED_IDENTITY_CLIENT_ID)

    def _get_managed_identity_assertion() -> str:
        return managed_identity.get_token(TOKEN_EXCHANGE_AUDIENCE).token

    return ClientAssertionCredential(
        tenant_id=tenant_id,
        client_id=signer_client_id,
        func=_get_managed_identity_assertion,
        authority=urlparse(AAD_AUTHORITY_URL).netloc,
    )
