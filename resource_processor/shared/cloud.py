from azure.cli.core import cloud


def get_cloud() -> cloud.Cloud:
    return cloud.get_active_cloud()


def get_acr_domain_suffix():
    return get_cloud().suffixes.acr_login_server_endpoint


def get_aad_authority_url() -> str:
    return get_cloud().endpoints.active_directory


def get_microsoft_graph_fqdn() -> str:
    return get_cloud().endpoints.microsoft_graph_resource_id.strip("/", "https://")
