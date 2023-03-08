import asyncio
from logging import Logger
import msal
from azure.identity.aio import ClientSecretCredential
from azure.identity import AzureAuthorityHosts
from msal.authority import AuthorityBuilder


supported_clouds = {'public': 'AZURE_PUBLIC_CLOUD', 'usgovernment': 'AZURE_GOVERNMENT'}


def get_auth_token_client_credentials(log: Logger,
                                      client_id: str,
                                      client_secret: str,
                                      aad_tenant_id: str,
                                      api_scope: str,
                                      verify: bool,
                                      cloud_name: str):
    try:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

        authority = get_authority(cloud_name)
        credential = ClientSecretCredential(aad_tenant_id, client_id, client_secret, connection_verify=verify, authority=authority)
        token = event_loop.run_until_complete(credential.get_token(f'{api_scope}/.default'))
        event_loop.run_until_complete(credential.close())

        event_loop.close()
        return token.token
    except Exception as ex:
        log.error(f"Failed to authenticate: {ex}")
        raise RuntimeError("Failed to get auth token")


def get_public_client_application(client_id: str,
                                  aad_tenant_id: str,
                                  token_cache,
                                  cloud_name: str):
    authority = get_authority(cloud_name)
    return msal.PublicClientApplication(
        client_id=client_id,
        authority=AuthorityBuilder(instance=authority, tenant=aad_tenant_id),
        token_cache=token_cache)


def get_authority(cloud_name: str):
    library_cloud_name = _get_cloud_name_for_libraries(cloud_name)
    return getattr(AzureAuthorityHosts(), library_cloud_name)


def _get_cloud_name_for_libraries(cloud_name: str):
    return supported_clouds.get(cloud_name, f"cloud_environment '{cloud_name}' is not supported. Supported environments are: {', '.join(supported_clouds.keys())}.")
