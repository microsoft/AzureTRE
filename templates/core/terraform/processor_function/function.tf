resource "azurerm_function_app" "procesorfunction" {
  name                       = "processor-func-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  app_service_plan_id        = var.app_service_plan_id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_access_key
  version = "~3"
  
  app_settings = {
        https_only = true
        FUNCTIONS_WORKER_RUNTIME = "python"
        FUNCTION_APP_EDIT_MODE = "readonly"
    }
}