# Resource deployment processor function

## Prerequisites


## Configuration

| Environment variable name | Description |
| ------------------------- | ----------- |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string. |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | *Optional for local testing.* Application Insights instrumentation key. |
| `RESOURCE_GROUP_NAME` |  |
| `VNET_NAME` |  |
| `ACI_SUBNET` |  |
| `CNAB_AZURE_STATE_STORAGE_ACCOUNT_NAME` |  |
| `SEC_CNAB_AZURE_STATE_STORAGE_ACCOUNT_KEY` |  |
| `CNAB_AZURE_STATE_PATH` |  |
| `CNAB_AZURE_STATE_FILESHARE` |  |
| `CNAB_AZURE_SUBSCRIPTION_ID` |  |
| `CNAB_AZURE_USER_MSI_RESOURCE_ID` |  |
| `CNAB_AZURE_VERBOSE` |  |
| `CNAB_AZURE_PROPAGATE_CREDENTIALS` |  |
| `CNAB_AZURE_MSI_TYPE` |  |
| `SEC_CNAB_AZURE_REGISTRY_USERNAME` |  |
| `SEC_CNAB_AZURE_REGISTRY_PASSWORD` |  |
| `REGISTRY_SERVER` |  |
| `SERVICE_BUS_CONNECTION_STRING` |  |
| `SERVICE_BUS_RESOURCE_REQUEST_QUEUE` |  |
| `SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE` |  |
| `WORKSPACES_PATH` |  |
| `CNAB_IMAGE` |  |
| `SEC_ARM_TENANT_ID` |  |
| `SEC_ARM_SUBSCRIPTION_ID` |  |
| `SEC_ARM_CLIENT_ID` |  |
| `SEC_ARM_CLIENT_SECRET` |  |
| `param_tfstate_resource_group_name` |  |
| `param_tfstate_container_name` |  |
| `param_tfstate_storage_account_name` |  |

    RESOURCE_GROUP_NAME                   = var.resource_group_name
    VNET_NAME                             = var.core_vnet
    ACI_SUBNET                            = var.aci_subnet
    CNAB_AZURE_STATE_STORAGE_ACCOUNT_NAME = var.mgmt_storage_account_name
    SEC_CNAB_AZURE_STATE_STORAGE_ACCOUNT_KEY  = data.azurerm_storage_account.state_storage.primary_access_key
    CNAB_AZURE_STATE_PATH                 = var.porter_output_container_name
    CNAB_AZURE_STATE_FILESHARE            = var.porter_output_container_name
    CNAB_AZURE_SUBSCRIPTION_ID            = data.azurerm_subscription.current.subscription_id
    CNAB_AZURE_USER_MSI_RESOURCE_ID       = var.identity_id
    CNAB_AZURE_VERBOSE                    = "true"
    CNAB_AZURE_PROPAGATE_CREDENTIALS      = "true"
    CNAB_AZURE_MSI_TYPE                   = "user"
    SEC_CNAB_AZURE_REGISTRY_USERNAME      = var.docker_registry_username
    SEC_CNAB_AZURE_REGISTRY_PASSWORD      = var.docker_registry_password
    REGISTRY_SERVER                       = var.docker_registry_server
    SERVICE_BUS_CONNECTION_STRING         = var.service_bus_connection_string
    SERVICE_BUS_RESOURCE_REQUEST_QUEUE    = var.service_bus_resource_request_queue
    SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE = var.service_bus_deployment_status_update_queue
    WORKSPACES_PATH                       = "/microsoft/azuretre/workspaces/"
    CNAB_IMAGE                            = "${var.docker_registry_server}.azurecr.io/microsoft/azuretre/cnab-aci:${var.management_api_image_tag}"
    SEC_ARM_CLIENT_ID                     = var.arm_client_id
    SEC_ARM_CLIENT_SECRET                 = var.arm_client_secret
    SEC_ARM_SUBSCRIPTION_ID               = data.azurerm_subscription.current.subscription_id
    SEC_ARM_TENANT_ID                     = data.azurerm_client_config.current.tenant_id
    param_tfstate_resource_group_name     = var.mgmt_resource_group_name
    param_tfstate_container_name          = var.terraform_state_container_name
    param_tfstate_storage_account_name    = var.mgmt_storage_account_name

## Running function locally

The Resource Processor is an Azure Function that can be hosted in [command line](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-cli-python?tabs=azure-cli%2Cbash%2Cbrowser#run-the-function-locally)

```cmd
func start
```

Or in [Visual Studio Code](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python#run-the-function-in-azure).
