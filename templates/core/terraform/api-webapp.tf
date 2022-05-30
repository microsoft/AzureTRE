data "local_file" "api_app_version" {
  filename = "${path.root}/../../../api_app/_version.py"
}

locals {
  version = replace(replace(replace(data.local_file.api_app_version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
}

resource "azurerm_static_site" "tre-ui" {
  name                = "ui-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.ui_location
}

resource "azurerm_app_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  reserved            = true
  kind                = "linux"

  lifecycle { ignore_changes = [tags] }

  sku {
    tier     = var.api_app_service_plan_sku_tier
    capacity = 1
    size     = var.api_app_service_plan_sku_size
  }
}

resource "azurerm_app_service" "api" {
  name                            = "api-${var.tre_id}"
  resource_group_name             = azurerm_resource_group.core.name
  location                        = azurerm_resource_group.core.location
  app_service_plan_id             = azurerm_app_service_plan.core.id
  https_only                      = true
  key_vault_reference_identity_id = azurerm_user_assigned_identity.id.id

  app_settings = {
    "APPLICATIONINSIGHTS_CONNECTION_STRING"      = module.azure_monitor.app_insights_connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY"             = module.azure_monitor.app_insights_instrumentation_key
    "APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL" = "True"
    "ApplicationInsightsAgent_EXTENSION_VERSION" = "~3"
    "XDT_MicrosoftApplicationInsights_Mode"      = "default"
    "WEBSITES_PORT"                              = "8000"
    "DOCKER_REGISTRY_SERVER_URL"                 = "https://${var.docker_registry_server}"
    "STATE_STORE_ENDPOINT"                       = azurerm_cosmosdb_account.tre-db-account.endpoint
    "COSMOSDB_ACCOUNT_NAME"                      = azurerm_cosmosdb_account.tre-db-account.name
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"      = "sb-${var.tre_id}.servicebus.windows.net"
    "SERVICE_BUS_RESOURCE_REQUEST_QUEUE"         = azurerm_servicebus_queue.workspacequeue.name
    "SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE" = azurerm_servicebus_queue.service_bus_deployment_status_update_queue.name
    "MANAGED_IDENTITY_CLIENT_ID"                 = azurerm_user_assigned_identity.id.client_id
    "TRE_ID"                                     = var.tre_id
    "RESOURCE_LOCATION"                          = azurerm_resource_group.core.location
    "SWAGGER_UI_CLIENT_ID"                       = var.swagger_ui_client_id
    "AAD_TENANT_ID"                              = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.auth_tenant_id.id})"
    "API_CLIENT_ID"                              = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.api_client_id.id})"
    "API_CLIENT_SECRET"                          = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.api_client_secret.id})"
    "RESOURCE_GROUP_NAME"                        = azurerm_resource_group.core.name
    "SUBSCRIPTION_ID"                            = data.azurerm_subscription.current.subscription_id
    CORE_ADDRESS_SPACE                           = var.core_address_space
    TRE_ADDRESS_SPACE                            = var.tre_address_space
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.id.id]
  }

  lifecycle { ignore_changes = [tags] }

  site_config {
    linux_fx_version                     = "DOCKER|${var.docker_registry_server}/${var.api_image_repository}:${local.version}"
    vnet_route_all_enabled               = true
    remote_debugging_enabled             = false
    scm_use_main_ip_restriction          = true
    acr_use_managed_identity_credentials = true
    acr_user_managed_identity_client_id  = azurerm_user_assigned_identity.id.client_id
    always_on                            = true
    min_tls_version                      = "1.2"
    ftps_state                           = "Disabled"
    websockets_enabled                   = false

    cors {
      allowed_origins     = ["https://${azurerm_static_site.tre-ui.default_host_name}", var.enable_local_debugging ? "http://localhost:3000" : ""]
      support_credentials = false
    }

    ip_restriction {
      action     = "Deny"
      ip_address = "0.0.0.0/0"
      name       = "Deny all"
      priority   = 2147483647
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
}

resource "azurerm_private_endpoint" "api_private_endpoint" {
  name                = "pe-api-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  subnet_id           = module.network.shared_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.api.id
    name                           = "psc-api-${var.tre_id}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [module.network.azurewebsites_dns_zone_id]
  }
}

resource "azurerm_app_service_virtual_network_swift_connection" "api-integrated-vnet" {
  app_service_id = azurerm_app_service.api.id
  subnet_id      = module.network.web_app_subnet_id
}

resource "azurerm_monitor_diagnostic_setting" "webapp_api" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_app_service.api.id
  log_analytics_workspace_id = module.azure_monitor.log_analytics_workspace_id

  log {
    category = "AppServiceHTTPLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  log {
    category = "AppServiceConsoleLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  log {
    category = "AppServiceAppLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  log {
    category = "AppServiceFileAuditLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  log {
    category = "AppServiceAuditLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  log {
    category = "AppServiceIPSecAuditLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  log {
    category = "AppServicePlatformLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  log {
    category = "AppServiceAntivirusScanAuditLogs"
    enabled  = true

    retention_policy {
      days    = 1
      enabled = false
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true

    retention_policy {
      enabled = false
    }
  }
}
