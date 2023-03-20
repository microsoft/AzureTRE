from azure.cli.core import cloud


def get_cloud() -> cloud.Cloud:
    return cloud.get_active_cloud()


def get_aad_authority_fqdn() -> str:
    return get_cloud().endpoints.active_directory.replace('https://', '')
