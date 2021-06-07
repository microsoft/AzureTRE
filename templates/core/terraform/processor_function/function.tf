data "azurerm_subscription" "current" {}

resource "azurerm_function_app" "procesorfunction" {
  name                       = "processor-func-${var.tre_id}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  app_service_plan_id        = var.app_service_plan_id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key
  version                    = "~3"
  os_type                    = "linux"
  app_settings = {
    https_only                            = true
    FUNCTIONS_WORKER_RUNTIME              = "python"
    FUNCTION_APP_EDIT_MODE                = "readonly"
    RESOURCE_GROUP_NAME                   = var.resource_group_name
    VNET_NAME                             = var.core_vnet
    ACI_SUBNET                            = var.aci_subnet
    CNAB_AZURE_STATE_STORAGE_ACCOUNT_NAME = var.storage_account_name
    CNAB_AZURE_STATE_STORAGE_ACCOUNT_KEY  = var.storage_account_access_key
    CNAB_AZURE_STATE_PATH                 = var.storage_state_path
    CNAB_AZURE_STATE_FILESHARE            = var.storage_state_path
    CNAB_AZURE_SUBSCRIPTION_ID            = data.azurerm_subscription.current.subscription_id
    CNAB_AZURE_USER_MSI_RESOURCE_ID       = var.identity_id
    CNAB_AZURE_VERBOSE                    = "true"
    CNAB_AZURE_PROPAGATE_CREDENTIALS      = "true"
    CNAB_AZURE_MSI_TYPE                   = "user"
    REGISTRY_USER_NAME                    = var.docker_registry_username
    REGISTRY_USER_PASSWORD                = var.docker_registry_password
    REGISTRY_SERVER                       = var.docker_registry_server
    servicebusconnection                  = var.servicebus_connection_string
    queueName                             = var.workspacequeue
  }
}
