from msrestazure.azure_cloud import AZURE_PUBLIC_CLOUD, AZURE_US_GOV_CLOUD
from core import config


def get_cloud():
    arm_env = config.ARM_ENVIRONMENT.lower()
    supported_clouds = {"public": AZURE_PUBLIC_CLOUD, "usgovernment": AZURE_US_GOV_CLOUD}
    if arm_env in supported_clouds:
        return supported_clouds[arm_env]
    raise ValueError("Invalid arm environment. Got: " + arm_env + " .Supported envs are: public and usgovernment.")


def get_authority():
    return get_cloud().endpoints.active_directory.replace("https://", "")


def get_aad_authority():
    return get_cloud().endpoints.active_directory


def get_resource_manager_endpoint():
    return get_cloud().endpoints.resource_manager


def get_resource_manager_credential_scopes():
    resource_manager_endpoint = get_resource_manager_endpoint()
    return [resource_manager_endpoint + ".default"]
