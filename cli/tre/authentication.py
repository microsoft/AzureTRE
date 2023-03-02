import asyncio
from logging import Logger
import msal
from azure.identity.aio import ClientSecretCredential
from msal.authority import AuthorityBuilder, AZURE_PUBLIC


def get_auth_token_client_credentials(
    log: Logger,
    client_id: str,
    client_secret: str,
    aad_tenant_id: str,
    api_scope: str,
    verify: bool
):
    try:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

        credential = ClientSecretCredential(aad_tenant_id, client_id, client_secret, connection_verify=verify)
        token = event_loop.run_until_complete(credential.get_token(f'{api_scope}/.default'))
        event_loop.run_until_complete(credential.close())

        event_loop.close()
        return token.token
    except Exception as ex:
        log.error(f"Failed to authenticate: {ex}")
        raise RuntimeError("Failed to get auth token")


def get_public_client_application(
    client_id: str,
    aad_tenant_id: str,
    token_cache
):
    return msal.PublicClientApplication(
        client_id=client_id,
        authority=AuthorityBuilder(AZURE_PUBLIC, aad_tenant_id),
        token_cache=token_cache)
