data "local_file" "airlock_processor_version" {
  filename = "${path.root}/../../../airlock_processor/_version.py"
}

locals {
  version = replace(replace(replace(data.local_file.airlock_processor_version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
}

resource "azurerm_service_plan" "airlock_plan" {
  name                = "plan-airlock-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.airlock_app_service_plan_sku_size
  tags                = var.tre_core_tags
  worker_count        = 1

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_account" "sa_airlock_processor_func_app" {
  name                            = local.airlock_function_sa_name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  tags                            = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_linux_function_app" "airlock_function_app" {
  name                       = local.airlock_function_app_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  https_only                 = true
  virtual_network_subnet_id  = var.airlock_processor_subnet_id
  service_plan_id            = azurerm_service_plan.airlock_plan.id
  storage_account_name       = azurerm_storage_account.sa_airlock_processor_func_app.name
  storage_account_access_key = azurerm_storage_account.sa_airlock_processor_func_app.primary_access_key
  tags                       = var.tre_core_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.airlock_id.id]
  }

  app_settings = {
    "SB_CONNECTION_STRING"                     = var.airlock_servicebus.default_primary_connection_string
    "BLOB_CREATED_TOPIC_NAME"                  = azurerm_servicebus_topic.blob_created.name
    "TOPIC_SUBSCRIPTION_NAME"                  = azurerm_servicebus_subscription.airlock_processor.name
    "EVENT_GRID_STEP_RESULT_TOPIC_URI_SETTING" = azurerm_eventgrid_topic.step_result.endpoint
    "EVENT_GRID_STEP_RESULT_TOPIC_KEY_SETTING" = azurerm_eventgrid_topic.step_result.primary_access_key
    "EVENT_GRID_TO_DELETE_TOPIC_URI_SETTING"   = azurerm_eventgrid_topic.to_delete.endpoint
    "EVENT_GRID_TO_DELETE_TOPIC_KEY_SETTING"   = azurerm_eventgrid_topic.to_delete.primary_access_key
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE"      = false
    "AIRLOCK_STATUS_CHANGED_QUEUE_NAME"        = local.status_changed_queue_name
    "AIRLOCK_SCAN_RESULT_QUEUE_NAME"           = local.scan_result_queue_name
    "AIRLOCK_TO_DELETE_QUEUE_NAME"             = local.to_delete_queue_name
    "ENABLE_MALWARE_SCANNING"                  = var.enable_malware_scanning
    "MANAGED_IDENTITY_CLIENT_ID"               = azurerm_user_assigned_identity.airlock_id.client_id
    "TRE_ID"                                   = var.tre_id
    "WEBSITE_CONTENTOVERVNET"                  = 1
  }

  site_config {
    always_on                                     = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.airlock_id.client_id
    container_registry_use_managed_identity       = true
    vnet_route_all_enabled                        = true
    ftps_state                                    = "Disabled"

    application_stack {
      docker {
        registry_url = var.docker_registry_server
        image_name   = var.airlock_processor_image_repository
        image_tag    = local.version
      }
    }

    # This is added automatically (by Azure?) when the equivalent is set in app_settings.
    # Setting it here to save TF from updating on every apply.
    application_insights_connection_string = var.applicationinsights_connection_string
  }

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_monitor_diagnostic_setting" "airlock_function_app" {
  name                       = "diagnostics-airlock-function-${var.tre_id}"
  target_resource_id         = azurerm_linux_function_app.airlock_function_app.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  log {
    category = "FunctionAppLogs"

    retention_policy {
      enabled = true
      days    = 365
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 365
    }
  }
}
