import logging
import os
from azure.cli.core import cloud


def _get_arm_environment():
    try:
        arm_environment = os.environ["ARM_ENVIRONMENT"].lower()
    except KeyError as e:
        logging.error(f'Missing environment variable: {e}')
        raise
    return arm_environment


# Get active cloud information such as endpoints and suffixes
def get_cloud() -> cloud.Cloud:
    arm_env = _get_arm_environment()
    supported_clouds = {"public": cloud.AZURE_PUBLIC_CLOUD, "usgovernment": cloud.AZURE_US_GOV_CLOUD}
    if arm_env in supported_clouds:
        return supported_clouds[arm_env]
    raise ValueError(
        f"Invalid arm environment. Got: {arm_env}. Supported envs are: {', '.join(supported_clouds.keys())}.")


def get_storage_endpoint() -> str:
    return get_cloud().suffixes.storage_endpoint
