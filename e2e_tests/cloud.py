from azure.cli.core import cloud
from urllib.parse import urlparse


def get_cloud() -> cloud.Cloud:
    return cloud.get_active_cloud()


def get_aad_authority_fqdn() -> str:
    return urlparse(get_cloud().endpoints.active_directory).netloc


def get_azurewebsites_root_domain() -> str:
    cloud_name = get_cloud().name
    root_domains = {cloud.AZURE_PUBLIC_CLOUD.name: "azurewebsites.net",
                    cloud.AZURE_US_GOV_CLOUD.name: "azurewebsites.us"}

    if cloud_name not in root_domains:
        raise ValueError(f"The root domain of 'azurewebsites' was not configured for '{cloud_name}'")

    return root_domains[cloud_name]
