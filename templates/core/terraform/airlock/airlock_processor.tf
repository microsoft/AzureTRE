data "local_file" "airlock_processor_version" {
  filename = "${path.root}/../../../airlock_processor/_version.py"
}

locals {
  version = replace(replace(replace(data.local_file.airlock_processor_version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
}

# re-using the id we have to access the acr
data "azurerm_user_assigned_identity" "id" {
  name                = "id-api-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

# re-using the web api app plan
data "azurerm_app_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

resource "azurerm_storage_account" "sa_airlock_processor_func_app" {
  name                     = local.airlock_function_app_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_linux_function_app" "airlock_function_app" {
  name                = local.airlock_function_app_name
  resource_group_name = var.resource_group_name
  location            = var.location

  storage_account_name = azurerm_storage_account.sa_airlock_processor_func_app.name
  service_plan_id      = data.azurerm_app_service_plan.core.id

  storage_account_access_key = azurerm_storage_account.sa_airlock_processor_func_app.primary_access_key

  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.id.id]
  }

  app_settings = {
    "SB_CONNECTION_STRING"                = data.azurerm_servicebus_namespace.airlock_sb.default_primary_connection_string
    "EVENT_GRID_TOPIC_URI_SETTING"        = azurerm_eventgrid_topic.step_result.endpoint
    "EVENT_GRID_TOPIC_KEY_SETTING"        = azurerm_eventgrid_topic.step_result.primary_access_key
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = false
  }

  site_config {
    always_on                                     = true
    container_registry_managed_identity_client_id = data.azurerm_user_assigned_identity.id.client_id
    container_registry_use_managed_identity       = true
    application_stack {
      docker {
        registry_url = var.docker_registry_server
        image_name   = var.airlock_processor_image_repository
        image_tag    = local.version
      }
    }
  }
}

