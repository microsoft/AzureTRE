from msrestazure.azure_cloud import AZURE_PUBLIC_CLOUD, AZURE_US_GOV_CLOUD
from core import config


def get_cloud():
    if config.ARM_ENVIRONMENT == "public":
        return AZURE_PUBLIC_CLOUD
    if config.ARM_ENVIRONMENT == "usgovernment":
        return AZURE_US_GOV_CLOUD


def get_authority():
    return get_cloud().endpoints.active_directory.replace("https://", "")
