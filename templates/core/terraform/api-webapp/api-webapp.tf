data "azurerm_subscription" "current" {}

resource "azurerm_app_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  reserved            = true
  kind                = "linux"

  lifecycle { ignore_changes = [tags] }

  sku {
    tier     = "PremiumV3"
    capacity = 1
    size     = "P1v3"
  }
}

resource "azurerm_app_service" "api" {
  name                = "api-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  app_service_plan_id = azurerm_app_service_plan.core.id
  https_only          = true

  app_settings = {
    "APPLICATIONINSIGHTS_CONNECTION_STRING"      = var.app_insights_connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY"             = var.app_insights_instrumentation_key
    "APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL" = "True"
    "ApplicationInsightsAgent_EXTENSION_VERSION" = "~3"
    "XDT_MicrosoftApplicationInsights_Mode"      = "default"
    "WEBSITES_PORT"                              = "8000"
    "WEBSITE_VNET_ROUTE_ALL"                     = 1
    "DOCKER_REGISTRY_SERVER_URL"                 = "https://${var.docker_registry_server}"
    "STATE_STORE_ENDPOINT"                       = var.state_store_endpoint
    "COSMOSDB_ACCOUNT_NAME"                      = var.cosmosdb_account_name
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"      = "sb-${var.tre_id}.servicebus.windows.net"
    "SERVICE_BUS_RESOURCE_REQUEST_QUEUE"         = var.service_bus_resource_request_queue
    "SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE" = var.service_bus_deployment_status_update_queue
    "MANAGED_IDENTITY_CLIENT_ID"                 = var.managed_identity.client_id
    "TRE_ID"                                     = var.tre_id
    "RESOURCE_LOCATION"                          = var.location
    "SWAGGER_UI_CLIENT_ID"                       = var.swagger_ui_client_id
    "AAD_TENANT_ID"                              = var.aad_tenant_id
    "API_CLIENT_ID"                              = var.api_client_id
    "API_CLIENT_SECRET"                          = var.api_client_secret
    "RESOURCE_GROUP_NAME"                        = var.resource_group_name
    "SUBSCRIPTION_ID"                            = data.azurerm_subscription.current.subscription_id
    CORE_ADDRESS_SPACE                           = var.core_address_space
    TRE_ADDRESS_SPACE                            = var.tre_address_space
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity.id]
  }

  lifecycle { ignore_changes = [tags] }

  site_config {
    linux_fx_version                     = "DOCKER|${var.docker_registry_server}/${var.api_image_repository}:${local.version}"
    remote_debugging_enabled             = false
    scm_use_main_ip_restriction          = true
    acr_use_managed_identity_credentials = true
    acr_user_managed_identity_client_id  = var.managed_identity.client_id

    cors {
      allowed_origins     = []
      support_credentials = false
    }

    always_on       = true
    min_tls_version = "1.2"

    ip_restriction {
      action     = "Deny"
      ip_address = "0.0.0.0/0"
      name       = "Deny all"
      priority   = 2147483647
    }

    ftps_state         = "FtpsOnly"
    websockets_enabled = false
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
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.shared_subnet

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.api.id
    name                           = "psc-api-${var.tre_id}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [var.azurewebsites_dns_zone_id]
  }
}

resource "azurerm_app_service_virtual_network_swift_connection" "api-integrated-vnet" {
  app_service_id = azurerm_app_service.api.id
  subnet_id      = var.web_app_subnet
}

resource "azurerm_monitor_diagnostic_setting" "webapp_api" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_app_service.api.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

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
