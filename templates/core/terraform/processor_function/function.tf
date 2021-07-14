data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

data "azurerm_storage_account" "state_storage" {
  name                = var.mgmt_storage_account_name
  resource_group_name = var.mgmt_resource_group_name
}

resource "azurerm_function_app" "procesorfunction" {
  name                       = "processor-func-${var.tre_id}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  app_service_plan_id        = var.app_service_plan_id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key
  version                    = "~3"
  os_type                    = "linux"

  site_config {
    always_on        = true
    linux_fx_version = "Python|3.8"
  }

  app_settings = {
    https_only                                 = true
    FUNCTIONS_WORKER_RUNTIME                   = "python"
    FUNCTION_APP_EDIT_MODE                     = "readonly"
    FUNCTIONS_EXTENSION_VERSION                = "~3"
    RESOURCE_GROUP_NAME                        = var.resource_group_name
    APPLICATIONINSIGHTS_CONNECTION_STRING      = var.app_insights_connection_string
    APPINSIGHTS_INSTRUMENTATIONKEY             = var.app_insights_instrumentation_key
    VNET_NAME                                  = var.core_vnet
    ACI_SUBNET                                 = var.aci_subnet
    CNAB_AZURE_STATE_STORAGE_ACCOUNT_NAME      = var.mgmt_storage_account_name
    SEC_CNAB_AZURE_STATE_STORAGE_ACCOUNT_KEY   = data.azurerm_storage_account.state_storage.primary_access_key
    CNAB_AZURE_STATE_PATH                      = var.porter_output_container_name
    CNAB_AZURE_STATE_FILESHARE                 = var.porter_output_container_name
    CNAB_AZURE_SUBSCRIPTION_ID                 = data.azurerm_subscription.current.subscription_id
    CNAB_AZURE_USER_MSI_RESOURCE_ID            = var.managed_identity.id
    CNAB_AZURE_VERBOSE                         = "true"
    CNAB_AZURE_PROPAGATE_CREDENTIALS           = "true"
    CNAB_AZURE_MSI_TYPE                        = "user"
    CNAB_AZURE_DELETE_RESOURCES                = false
    CNAB_AZURE_DELETE_OUTPUTS_FROM_FILESHARE   = false
    SEC_CNAB_AZURE_REGISTRY_USERNAME           = var.docker_registry_username
    SEC_CNAB_AZURE_REGISTRY_PASSWORD           = var.docker_registry_password
    REGISTRY_SERVER                            = var.docker_registry_server
    SERVICE_BUS_CONNECTION_STRING              = var.service_bus_connection_string
    SERVICE_BUS_RESOURCE_REQUEST_QUEUE         = var.service_bus_resource_request_queue
    SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE = var.service_bus_deployment_status_update_queue
    WORKSPACES_PATH                            = "/"
    CNAB_IMAGE                                 = "${var.docker_registry_server}/microsoft/azuretre/cnab-aci:${var.management_api_image_tag}"
    SEC_ARM_CLIENT_ID                          = var.arm_client_id
    SEC_ARM_CLIENT_SECRET                      = var.arm_client_secret
    SEC_ARM_SUBSCRIPTION_ID                    = data.azurerm_subscription.current.subscription_id
    SEC_ARM_TENANT_ID                          = data.azurerm_client_config.current.tenant_id
    param_tfstate_resource_group_name          = var.mgmt_resource_group_name
    param_tfstate_container_name               = var.terraform_state_container_name
    param_tfstate_storage_account_name         = var.mgmt_storage_account_name
    MANAGED_IDENTITY_CLIENT_ID                 = var.managed_identity.client_id
    ENABLE_ORYX_BUILD                          = true
    SCM_DO_BUILD_DURING_DEPLOYMENT             = true
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity.id]
  }

  lifecycle { ignore_changes = [tags] }
}
