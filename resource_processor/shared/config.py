import os
from _version import __version__
from shared.logging import logger, tracer


VERSION = __version__


def get_config() -> dict:
    with tracer.start_as_current_span("get_config"):
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
        config["key_vault_url"] = os.environ.get("KEY_VAULT_URL", os.environ.get("KEYVAULT_URI", None))
        config["arm_environment"] = os.environ.get("ARM_ENVIRONMENT", "public")
        config["azure_environment"] = os.environ.get("AZURE_ENVIRONMENT", "AzureCloud")
        config["aad_authority_url"] = os.environ.get("AAD_AUTHORITY_URL", "https://login.microsoftonline.com")
        config["microsoft_graph_fqdn"] = os.environ.get("MICROSOFT_GRAPH_FQDN", "graph.microsoft.com")

        try:
            config["number_processes_int"] = int(config["number_processes"])
        except ValueError:
            logger.info("Invalid setting for NUMBER_PROCESSES, will default to 1")
            config["number_processes_int"] = 1

        # Needed for running porter
        config["arm_use_msi"] = os.environ.get("ARM_USE_MSI", "false")
        config["arm_subscription_id"] = os.environ["AZURE_SUBSCRIPTION_ID"]
        config["arm_client_id"] = os.environ["ARM_CLIENT_ID"]
        config["arm_tenant_id"] = os.environ["AZURE_TENANT_ID"]

        if config["arm_use_msi"] == "false":
            # These are needed when running locally
            config["arm_client_secret"] = os.environ["ARM_CLIENT_SECRET"]
            config["aad_tenant_id"] = os.environ["AAD_TENANT_ID"]
            config["application_admin_client_id"] = os.environ["APPLICATION_ADMIN_CLIENT_ID"]
            config["application_admin_client_secret"] = os.environ["APPLICATION_ADMIN_CLIENT_SECRET"]

        else:
            config["arm_client_secret"] = ""  # referenced in the credential set

        # when running in vscode devcontainer
        if "DEVCONTAINER" in os.environ:
            config["remote_containers_ipc"] = os.environ["REMOTE_CONTAINERS_IPC"]

        # Create env dict for porter
        config["porter_env"] = {
            "HOME": os.environ["HOME"],
            "PATH": os.environ["PATH"],
            "KEY_VAULT_URL": config["key_vault_url"],
            "ARM_ENVIRONMENT": config["arm_environment"],
            "AZURE_ENVIRONMENT": config["azure_environment"],

            # These are needed since they are referenced as credentials in every bundle and also in arm_auth credential set.
            "ARM_CLIENT_ID": config["arm_client_id"],
            "ARM_CLIENT_SECRET": config["arm_client_secret"],
            "ARM_SUBSCRIPTION_ID": config["arm_subscription_id"],
            "ARM_TENANT_ID": config["arm_tenant_id"],
        }

        if config["arm_use_msi"] == "false":
            config["porter_env"].update(
                {
                    "AAD_TENANT_ID": config["aad_tenant_id"],
                    "APPLICATION_ADMIN_CLIENT_ID": config["application_admin_client_id"],
                    "APPLICATION_ADMIN_CLIENT_SECRET": config["application_admin_client_secret"],
                }
            )

        # when running in vscode devcontainer
        if "DEVCONTAINER" in os.environ:
            config["porter_env"].update(
                {
                    "REMOTE_CONTAINERS_IPC": config["remote_containers_ipc"]
                }
            )

        # Load env vars for bundles
        def envvar_to_key(name: str) -> str:
            return name[len("RP_BUNDLE_"):].lower()

        config["bundle_params"] = {
            envvar_to_key(env_var_name): os.getenv(env_var_name)
            for env_var_name in os.environ
            if env_var_name.startswith("RP_BUNDLE")
        }

    return config
