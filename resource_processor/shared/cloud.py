from azure.cli.core import cloud
from resource_processor.shared import config


# Get active cloud information such as endpoints and suffixes
def get_cloud() -> cloud.Cloud:
    arm_env = config["arm_environment"].lower()
    supported_clouds = {"public": cloud.AZURE_PUBLIC_CLOUD, "usgovernment": cloud.AZURE_US_GOV_CLOUD}
    if arm_env in supported_clouds:
        return supported_clouds[arm_env]
    raise ValueError(
        f"Invalid arm environment. Got: {arm_env}. Supported envs are: {', '.join(supported_clouds.keys())}.")


def get_acr_domain_suffix():
    return get_cloud().suffixes.acr_login_server_endpoint


def get_aad_authority_fqdn() -> str:
    return get_cloud().endpoints.active_directory
