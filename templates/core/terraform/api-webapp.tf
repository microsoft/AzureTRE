data "local_file" "api_app_version" {
  filename = "${path.root}/../../../api_app/_version.py"
}

locals {
  version = replace(replace(replace(data.local_file.api_app_version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
}

resource "azurerm_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  os_type             = "Linux"
  sku_name            = var.api_app_service_plan_sku_size
  tags                = local.tre_core_tags
  worker_count        = 1
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_linux_web_app" "api" {
  name                            = "api-${var.tre_id}"
  resource_group_name             = azurerm_resource_group.core.name
  location                        = azurerm_resource_group.core.location
  service_plan_id                 = azurerm_service_plan.core.id
  https_only                      = true
  key_vault_reference_identity_id = azurerm_user_assigned_identity.id.id
  virtual_network_subnet_id       = module.network.web_app_subnet_id
  tags                            = local.tre_core_tags

  app_settings = {
    "APPLICATIONINSIGHTS_CONNECTION_STRING"          = module.azure_monitor.app_insights_connection_string
    "APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL"     = "True"
    "ApplicationInsightsAgent_EXTENSION_VERSION"     = "~3"
    "XDT_MicrosoftApplicationInsights_Mode"          = "default"
    "WEBSITES_PORT"                                  = "8000"
    "STATE_STORE_ENDPOINT"                           = azurerm_cosmosdb_account.tre_db_account.endpoint
    "COSMOSDB_ACCOUNT_NAME"                          = azurerm_cosmosdb_account.tre_db_account.name
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"          = "sb-${var.tre_id}.servicebus.windows.net"
    "EVENT_GRID_STATUS_CHANGED_TOPIC_ENDPOINT"       = module.airlock_resources.event_grid_status_changed_topic_endpoint
    "EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_ENDPOINT" = module.airlock_resources.event_grid_airlock_notification_topic_endpoint
    "SERVICE_BUS_RESOURCE_REQUEST_QUEUE"             = azurerm_servicebus_queue.workspacequeue.name
    "SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE"     = azurerm_servicebus_queue.service_bus_deployment_status_update_queue.name
    "SERVICE_BUS_STEP_RESULT_QUEUE"                  = module.airlock_resources.service_bus_step_result_queue
    "MANAGED_IDENTITY_CLIENT_ID"                     = azurerm_user_assigned_identity.id.client_id
    "TRE_ID"                                         = var.tre_id
    "RESOURCE_LOCATION"                              = azurerm_resource_group.core.location
    "SWAGGER_UI_CLIENT_ID"                           = var.swagger_ui_client_id
    "AAD_TENANT_ID"                                  = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.auth_tenant_id.id})"
    "API_CLIENT_ID"                                  = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.api_client_id.id})"
    "API_CLIENT_SECRET"                              = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.api_client_secret.id})"
    "RESOURCE_GROUP_NAME"                            = azurerm_resource_group.core.name
    "SUBSCRIPTION_ID"                                = data.azurerm_subscription.current.subscription_id
    CORE_ADDRESS_SPACE                               = var.core_address_space
    TRE_ADDRESS_SPACE                                = var.tre_address_space
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.id.id]
  }

  lifecycle {
    ignore_changes = [
      tags,
    ]
  }

  site_config {
    vnet_route_all_enabled                        = true
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.id.client_id
    minimum_tls_version                           = "1.2"
    ftps_state                                    = "Disabled"

    application_stack {
      docker_image     = "${var.docker_registry_server}/${var.api_image_repository}"
      docker_image_tag = local.version
    }

    cors {
      allowed_origins = [
        var.enable_local_debugging ? "http://localhost:3000" : ""
      ]
    }
  }

  logs {
    application_logs {
      file_system_level = "Information"
    }

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 100
      }
    }
  }

  depends_on = [
    module.airlock_resources
  ]
}

resource "azurerm_private_endpoint" "api_private_endpoint" {
  name                = "pe-api-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  subnet_id           = module.network.shared_subnet_id
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.api.id
    name                           = "psc-api-${var.tre_id}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [module.network.azurewebsites_dns_zone_id]
  }
}

resource "azurerm_monitor_diagnostic_setting" "webapp_api" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_linux_web_app.api.id
  log_analytics_workspace_id = module.azure_monitor.log_analytics_workspace_id

  dynamic "log" {
    for_each = data.azurerm_monitor_diagnostic_categories.api.logs
    content {
      category = log.value
      enabled  = contains(local.api_diagnostic_categories_enabled, log.value) ? true : false

      retention_policy {
        enabled = contains(local.api_diagnostic_categories_enabled, log.value) ? true : false
        days    = 365
      }
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
