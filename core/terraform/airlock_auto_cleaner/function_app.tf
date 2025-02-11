resource "azurerm_service_plan" "airlock_auto_cleaner" {
  name                = "asp-airlock-auto-cleaner"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "P1v2"
}

resource "azurerm_application_insights" "airlock_auto_cleaner" {
  name                = "app-insights-airlock-auto-cleaner"
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
}

# This ID will be used for the Function App for downloading the function code and authentication.
resource "azurerm_user_assigned_identity" "function_app_airlock_auto_cleaner_identity" {
  name                = "id-function-app-airlock-auto-cleaner"
  location            = var.location
  resource_group_name = var.resource_group_name
}

# Role required for reading from Storage Account.
resource "azurerm_role_assignment" "assign_identity_storage_blob_data_contributor" {
  scope                = azurerm_storage_account.airlock_auto_cleaner.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.principal_id
}

# Role required for listing Resource Groups.
resource "azurerm_role_assignment" "assign_identity_reader" {
  scope                = data.azurerm_subscription.primary.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.principal_id
}

# Role required for deallocating VMs.
resource "azurerm_role_assignment" "assign_identity_vm_contributor" {
  scope                = data.azurerm_subscription.primary.id
  role_definition_name = "Desktop Virtualization Virtual Machine Contributor"
  principal_id         = azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.principal_id
}

data "http" "my_ip_address" {
  url = "http://ifconfig.net"
}

# Only for debugging.
output "my_ip_address" {
  value = data.http.my_ip_address.response_body
}

resource "azurerm_storage_account" "airlock_auto_cleaner" {
  name                     = "vmautostopper"
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "LRS"

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.id
    ]
  }

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
    ip_rules       = ["${chomp(data.http.my_ip_address.response_body)}"]
  }

  public_network_access_enabled = false
}

# Storage container for storing Function App code/releases.
resource "azurerm_storage_container" "airlock_auto_cleaner" {
  name                 = "airlock-auto-cleaner"
  storage_account_name = azurerm_storage_account.airlock_auto_cleaner.name
}

resource "azurerm_private_endpoint" "airlock_auto_cleaner" {
  name                = "pe-airlock-auto-cleaner"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet_id

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "pesc-airlock-auto-cleaner"
    private_connection_resource_id = azurerm_storage_account.airlock_auto_cleaner.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# Create Function App resource.
# The code will be loaded from a ZIP file stored in a blob storage container.
resource "azurerm_linux_function_app" "airlock_auto_cleaner" {
  name                = "func-airlock-auto-cleaner"
  resource_group_name = var.resource_group_name
  location            = var.location

  identity {
    type = "UserAssigned"
    identity_ids = [
      azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.id
    ]
  }

  # auth_settings {
  #   enabled = true
  #   active_directory {
  #     client_id = azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.id
  #   }
  # }

  storage_account_name       = azurerm_storage_account.airlock_auto_cleaner.name
  storage_account_access_key = azurerm_storage_account.airlock_auto_cleaner.primary_access_key
  service_plan_id            = azurerm_service_plan.airlock_auto_cleaner.id
  builtin_logging_enabled    = false

  # This configuration makes the Function App runs from a file
  # stored in tha blob storage container.
  app_settings = {
    "WEBSITE_RUN_FROM_PACKAGE"                     = "https://${azurerm_storage_account.airlock_auto_cleaner.name}.blob.core.windows.net/${azurerm_storage_container.airlock_auto_cleaner.name}/${azurerm_storage_blob.airlock_auto_cleaner.name}"
    "WEBSITE_RUN_FROM_PACKAGE_BLOB_MI_RESOURCE_ID" = azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.id
    "MANAGED_IDENTITY_CLIENT_ID"                   = azurerm_user_assigned_identity.function_app_airlock_auto_cleaner_identity.client_id
    "WEBSITE_TIME_ZONE"                            = local.execution_tizezone                        
    "SUBSCRIPTION_ID"                              = data.azurerm_client_config.current.subscription_id
    "ENVIRONMENT_NAME"                             = local.environment_name
    "APPINSIGHTS_INSTRUMENTATIONKEY"               = azurerm_application_insights.airlock_auto_cleaner.instrumentation_key
  }

  # We are running a Python app.
  site_config {
    application_stack {
      python_version = "3.10"
    }
    application_insights_connection_string = azurerm_application_insights.airlock_auto_cleaner.connection_string
    application_insights_key               = azurerm_application_insights.airlock_auto_cleaner.instrumentation_key
    always_on                              = true
  }

  # This is the subnet used for VNet integration.
  virtual_network_subnet_id = var.web_app_subnet_id
}

# Upload Function App's code.
resource "azurerm_storage_blob" "airlock_auto_cleaner" {
  name                   = "func-airlock-auto-cleaner.zip"
  storage_account_name   = azurerm_storage_account.airlock_auto_cleaner.name
  storage_container_name = azurerm_storage_container.airlock_auto_cleaner.name
  type                   = "Block"
  source                 = "func-airlock-auto-cleaner.zip"
}
