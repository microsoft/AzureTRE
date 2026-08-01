from typing import Optional
from urllib.parse import urlparse

from azure.core.exceptions import ResourceNotFoundError
from azure.keyvault.secrets import KeyVaultSecretIdentifier
from azure.keyvault.secrets.aio import SecretClient

from core import credentials
from resources import strings
from services.logging import logger


# Convention: any resource property whose name contains this token holds a
# Key Vault secret identifier rather than the secret value itself.
KEYVAULT_SECRET_ID_TOKEN = "keyvault_secret_id"


def is_secret_property(property_name: str) -> bool:
    """Return True if the property name follows the secret naming convention."""
    return KEYVAULT_SECRET_ID_TOKEN in property_name


async def get_secret_value(keyvault_secret_id: str, expected_keyvault_uri: Optional[str] = None) -> str:
    """Retrieve a secret value from a workspace Key Vault.

    The ``keyvault_secret_id`` is a full Key Vault secret identifier (URI) as
    output by a resource template. When ``expected_keyvault_uri`` is provided the
    secret's vault must match it, ensuring a resource can only expose secrets that
    live in its own workspace Key Vault.
    """
    try:
        parsed_secret_id = KeyVaultSecretIdentifier(keyvault_secret_id)
    except ValueError:
        raise SecretRetrievalError(strings.INVALID_KEYVAULT_SECRET_ID)

    if expected_keyvault_uri and not _same_vault(parsed_secret_id.vault_url, expected_keyvault_uri):
        raise SecretRetrievalError(strings.KEYVAULT_SECRET_OUTSIDE_WORKSPACE)

    async with credentials.get_credential_async_context() as credential:
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
