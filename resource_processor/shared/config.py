import os
import sys


class ProcessorConfig:
    def __init__(self, logger):
        try:
            self.initialize_config()
        except KeyError as e:
            logger.error(f"Environment variable {e} is not set correctly...Exiting")
            sys.exit(1)

    def initialize_config(self):
        self.registry_server = os.environ["REGISTRY_SERVER"]
        self.tfstate_container_name = os.environ["TERRAFORM_STATE_CONTAINER_NAME"]
        self.tfstate_resource_group_name = os.environ["MGMT_RESOURCE_GROUP_NAME"]
        self.tfstate_storage_account_name = os.environ["MGMT_STORAGE_ACCOUNT_NAME"]
        self.deployment_status_queue = os.environ["SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE"]
        self.resource_request_queue = os.environ["SERVICE_BUS_RESOURCE_REQUEST_QUEUE"]
        self.service_bus_namespace = os.environ["SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"]
        self.vmss_msi_id = os.environ.get("VMSS_MSI_ID", None)

        # Needed for running porter
        self.arm_use_msi = os.environ.get("ARM_USE_MSI", "false")
        self.arm_subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
        self.arm_client_id = os.environ["ARM_CLIENT_ID"]
        self.arm_tenant_id = os.environ["AZURE_TENANT_ID"]

        # Whether to use local az credentials for connecting to Service Bus (for local debugging)
        self.use_local_creds = os.environ.get("USE_LOCAL_CREDS", "false")

        # Only set client secret if MSI is disabled
        self.arm_client_secret = os.environ["ARM_CLIENT_SECRET"] if self.arm_use_msi == "false" else ""

        # Create env dict for porter
        self.porter_env = {
            "HOME": os.environ["HOME"],
            "PATH": os.environ["PATH"],
            "ARM_CLIENT_ID": self.arm_client_id,
            "ARM_CLIENT_SECRET": self.arm_client_secret,
            "ARM_SUBSCRIPTION_ID": self.arm_subscription_id,
            "ARM_TENANT_ID": self.arm_tenant_id
        }
