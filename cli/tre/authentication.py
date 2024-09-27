import asyncio
from logging import Logger
import msal
from azure.identity.aio import ClientSecretCredential
from azure.cli.core import cloud
from urllib.parse import urlparse
from msal.authority import AuthorityBuilder


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

        credential = ClientSecretCredential(aad_tenant_id, client_id, client_secret, connection_verify=verify, authority=get_aad_authority_fqdn())
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
        authority=AuthorityBuilder(instance=get_aad_authority_fqdn(), tenant=aad_tenant_id),
        token_cache=token_cache)


def get_cloud() -> cloud.Cloud:
    return cloud.get_active_cloud()


def get_aad_authority_fqdn() -> str:
    return urlparse(get_cloud().endpoints.active_directory).netloc
