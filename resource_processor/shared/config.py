import os

from _version import __version__

VERSION = __version__


def get_config(logger_adapter) -> dict:
    config = {}

    config["registry_server"] = os.environ["REGISTRY_SERVER"]
    config["tfstate_container_name"] = os.environ["TERRAFORM_STATE_CONTAINER_NAME"]
    config["tfstate_resource_group_name"] = os.environ["MGMT_RESOURCE_GROUP_NAME"]
    config["tfstate_storage_account_name"] = os.environ["MGMT_STORAGE_ACCOUNT_NAME"]
    config["deployment_status_queue"] = os.environ["SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE"]
    config["resource_request_queue"] = os.environ["SERVICE_BUS_RESOURCE_REQUEST_QUEUE"]
    config["service_bus_namespace"] = os.environ["SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"]
    config["vmss_msi_id"] = os.environ.get("VMSS_MSI_ID", None)
    config["number_processes"] = os.environ.get("NUMBER_PROCESSES", "1")

    try:
        config["number_processes_int"] = int(config["number_processes"])
    except ValueError:
        logger_adapter.info("Invalid setting for NUMBER_PROCESSES, will default to 1")
        config["number_processes_int"] = 1

    # Needed for running porter
    config["arm_use_msi"] = os.environ.get("ARM_USE_MSI", "false")
    config["arm_subscription_id"] = os.environ["AZURE_SUBSCRIPTION_ID"]
    config["arm_client_id"] = os.environ["ARM_CLIENT_ID"]
    config["arm_tenant_id"] = os.environ["AZURE_TENANT_ID"]

    # Only set client secret if MSI is disabled
    config["arm_client_secret"] = os.environ["ARM_CLIENT_SECRET"] if config["arm_use_msi"] == "false" else ""

    # Create env dict for porter
    config["porter_env"] = {
        "HOME": os.environ["HOME"],
        "PATH": os.environ["PATH"],
        "ARM_CLIENT_ID": config["arm_client_id"],
        "ARM_CLIENT_SECRET": config["arm_client_secret"],
        "ARM_SUBSCRIPTION_ID": config["arm_subscription_id"],
        "ARM_TENANT_ID": config["arm_tenant_id"]
    }

    return config
