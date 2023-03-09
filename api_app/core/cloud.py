from azure.cli.core import cloud
from core import config


# Get active cloud information such as endpoints and suffixes
def get_cloud() -> cloud.Cloud:
    arm_env = config.ARM_ENVIRONMENT.lower()
    supported_clouds = {"public": cloud.AZURE_PUBLIC_CLOUD, "usgovernment": cloud.AZURE_US_GOV_CLOUD}
    if arm_env in supported_clouds:
        return supported_clouds[arm_env]
    raise ValueError(
        f"Invalid arm environment. Got: {arm_env}. Supported envs are: {', '.join(supported_clouds.keys())}.")


def get_aad_authority_fqdn() -> str:
    return get_cloud().endpoints.active_directory.replace("https://", "")


def get_aad_authority_url() -> str:
    return get_cloud().endpoints.active_directory


def get_resource_manager_endpoint() -> str:
    return get_cloud().endpoints.resource_manager


def get_resource_manager_credential_scopes():
    resource_manager_endpoint = get_resource_manager_endpoint()
    return [resource_manager_endpoint + ".default"]
