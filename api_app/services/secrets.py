from typing import Optional
from urllib.parse import urlparse

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import ManagedIdentityCredential
from azure.identity.aio import OnBehalfOfCredential
from azure.keyvault.secrets import KeyVaultSecretIdentifier
from azure.keyvault.secrets.aio import SecretClient

from core.config import AAD_AUTHORITY_URL, AAD_TENANT_ID, MANAGED_IDENTITY_CLIENT_ID
from resources import strings
from services.logging import logger


# Convention: any resource property whose name contains this token holds a
# Key Vault secret identifier rather than the secret value itself.
KEYVAULT_SECRET_ID_TOKEN = "keyvault_secret_id"

# Audience used when the API's managed identity requests a token to use as the
# client assertion in the On-Behalf-Of exchange. The managed identity is
# configured as a federated identity credential on the workspace app
# registration, so this token replaces a stored client secret.
TOKEN_EXCHANGE_SCOPE = "api://AzureADTokenExchange/.default"


def is_secret_property(property_name: str) -> bool:
    """Return True if the property name follows the secret naming convention."""
    return KEYVAULT_SECRET_ID_TOKEN in property_name


def _get_client_assertion() -> str:
    """Return a managed identity token to use as the OBO client assertion.

    The API's managed identity is registered as a federated identity credential
    on the workspace app registration. A managed identity token for the token
    exchange audience is therefore accepted by Entra ID in place of a workspace
    client secret, so no secret needs to be stored or rotated.
    """
    credential = ManagedIdentityCredential(client_id=MANAGED_IDENTITY_CLIENT_ID)
    try:
        return credential.get_token(TOKEN_EXCHANGE_SCOPE).token
    finally:
        credential.close()


def _get_obo_credential(workspace_client_id: str, user_token: str) -> OnBehalfOfCredential:
    """Build an On-Behalf-Of credential for the workspace app registration.

    The workspace app registration acts as the confidential client, using the
    federated managed identity assertion to authenticate, and exchanges the
    caller's token so that downstream Key Vault access is performed on behalf of
    the signed-in user.
    """
    return OnBehalfOfCredential(
        tenant_id=AAD_TENANT_ID,
        client_id=workspace_client_id,
        user_assertion=user_token,
        client_assertion_func=_get_client_assertion,
        authority=urlparse(AAD_AUTHORITY_URL).netloc,
    )


async def get_secret_value(
    keyvault_secret_id: str,
    expected_keyvault_uri: Optional[str] = None,
    workspace_client_id: Optional[str] = None,
    user_token: Optional[str] = None,
) -> str:
    """Retrieve a secret value from a workspace Key Vault on behalf of the user.

    The ``keyvault_secret_id`` is a full Key Vault secret identifier (URI) as
    output by a resource template. When ``expected_keyvault_uri`` is provided the
    secret's vault must match it, ensuring a resource can only expose secrets that
    live in its own workspace Key Vault.

    ``workspace_client_id`` (the workspace app registration client id) and
    ``user_token`` (the caller's access token) are used to perform an
    On-Behalf-Of exchange so Key Vault access is authorised as the signed-in
    user rather than the API's own identity.
    """
    if not workspace_client_id or not user_token:
        raise SecretRetrievalError(strings.UNABLE_TO_RETRIEVE_KEYVAULT_SECRET)

    try:
        parsed_secret_id = KeyVaultSecretIdentifier(keyvault_secret_id)
    except ValueError:
        raise SecretRetrievalError(strings.INVALID_KEYVAULT_SECRET_ID)

    if expected_keyvault_uri and not _same_vault(parsed_secret_id.vault_url, expected_keyvault_uri):
        raise SecretRetrievalError(strings.KEYVAULT_SECRET_OUTSIDE_WORKSPACE)

    async with _get_obo_credential(workspace_client_id, user_token) as credential:
        async with SecretClient(vault_url=parsed_secret_id.vault_url, credential=credential) as secret_client:
            try:
                secret = await secret_client.get_secret(parsed_secret_id.name)
            except ResourceNotFoundError:
                raise SecretRetrievalError(strings.KEYVAULT_SECRET_NOT_FOUND)
            except Exception:
                logger.exception("Failed to retrieve secret from Key Vault")
                raise SecretRetrievalError(strings.UNABLE_TO_RETRIEVE_KEYVAULT_SECRET)

    return secret.value


def _same_vault(vault_url_a: str, vault_url_b: str) -> bool:
    return urlparse(vault_url_a).netloc.lower() == urlparse(vault_url_b).netloc.lower()


class SecretRetrievalError(Exception):
    """Raised when a workspace Key Vault secret cannot be retrieved."""
