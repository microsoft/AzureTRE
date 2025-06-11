# This Managed ID will be used for the Function App for downloading the function code and authentication.
# For reading data from KeyVaults we must create the corresponding role assignments.
resource "azurerm_user_assigned_identity" "function_app_data_usage_enforcement_identity" {
  name                = "id-app-data-usage-enforcement-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
}

# Role required for reading from Storage Account.
resource "azurerm_role_assignment" "assign_identity_storage_blob_data_contributor" {
  scope                = data.azurerm_storage_account.stg.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function_app_data_usage_enforcement_identity.principal_id
}

# Role required at Subscription level for listing Resource Groups.
resource "azurerm_role_assignment" "assign_identity_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.function_app_data_usage_enforcement_identity.principal_id
}

# Getting IP address for enabling access to
data "http" "my_ip_address" {
  url = "https://ipecho.net/plain"
}

# Only for debugging.
output "my_ip_address" {
  value = data.http.my_ip_address.response_body
}

# Let's wait a little bit for the Storage account creation settles down. :)
resource "time_sleep" "wait_for_storage_account_creation" {
  create_duration = "30s"

  depends_on = [
    azurerm_role_assignment.assign_identity_storage_blob_data_contributor
  ]
}

# Storage container for storing Function App code/releases.
resource "azurerm_storage_container" "data_usage_enforcement" {
  name                 = "data-usage-enforcement-${var.tre_id}"
  storage_account_name = data.azurerm_storage_account.stg.name

  depends_on = [
    time_sleep.wait_for_storage_account_creation
  ]
}

# Create Function App resource.
# The code will be loaded from a ZIP file stored in a blob storage container.
resource "azurerm_linux_function_app" "data_usage_enforcement" {
  name                = "func-data-usage-enforcement-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tre_core_tags

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.function_app_data_usage_enforcement_identity.id
    ]
  }

  storage_account_name       = data.azurerm_storage_account.stg.name
  storage_account_access_key = data.azurerm_storage_account.stg.primary_access_key
  service_plan_id            = data.azurerm_service_plan.core.id
  builtin_logging_enabled    = false

  # This configuration makes the Function App runs from a file
  # stored in tha blob storage container.
  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"                     = "https://${data.azurerm_storage_account.stg.name}.blob.core.windows.net/${azurerm_storage_container.data_usage_enforcement.name}/${azurerm_storage_blob.data_usage_enforcement.name}"
    "WEBSITE_RUN_FROM_PACKAGE_BLOB_MI_RESOURCE_ID" = azurerm_user_assigned_identity.function_app_data_usage_enforcement_identity.id
    "MANAGED_IDENTITY_CLIENT_ID"                   = azurerm_user_assigned_identity.function_app_data_usage_enforcement_identity.client_id
    "WEBSITE_TIME_ZONE"                            = local.execution_tizezone
    "SUBSCRIPTION_ID"                              = data.azurerm_client_config.current.subscription_id
    "ENVIRONMENT_PREFIX"                           = local.environment_prefix
    "APPINSIGHTS_INSTRUMENTATIONKEY"               = data.azurerm_application_insights.core.instrumentation_key
    "FUNCTIONS_WORKER_RUNTIME"                     = "python"
    "CORE_STORAGE_ACCESS_KEY"                      = data.azurerm_storage_account.stg.primary_access_key
  }

  # We are running a Python app.
  site_config {
    application_stack {
      python_version = "3.10"
    }
    application_insights_connection_string = data.azurerm_application_insights.core.connection_string
    application_insights_key               = data.azurerm_application_insights.core.instrumentation_key
    always_on                              = true
  }

  # This is the subnet used for VNet integration.
  virtual_network_subnet_id = var.web_app_subnet_id
}

# Upload Function App's code.
resource "azurerm_storage_blob" "data_usage_enforcement" {
  name                   = "func-data-usage-enforcement.zip"
  storage_account_name   = data.azurerm_storage_account.stg.name
  storage_container_name = azurerm_storage_container.data_usage_enforcement.name
  type                   = "Block"
  source                 = "${path.root}/func-data-usage-enforcement.zip"
}
