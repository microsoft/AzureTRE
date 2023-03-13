from azure.cli.core import cloud


# Get active cloud information such as endpoints and suffixes
def get_cloud() -> cloud.Cloud:
    return cloud.get_active_cloud()


def get_storage_endpoint() -> str:
    return get_cloud().suffixes.storage_endpoint
