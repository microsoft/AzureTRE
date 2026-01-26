from azure.cli.core import cloud
from urllib.parse import urlparse


def get_cloud() -> cloud.Cloud:
    return cloud.get_active_cloud()


def get_aad_authority_fqdn() -> str:
    return urlparse(get_cloud().endpoints.active_directory).netloc


def get_ms_graph_resource() -> str:
    """Return the Microsoft Graph resource ID for the active cloud."""
    return get_cloud().endpoints.microsoft_graph_resource_id.rstrip("/")
