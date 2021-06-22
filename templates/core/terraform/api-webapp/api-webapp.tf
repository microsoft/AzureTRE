resource "azurerm_app_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  reserved            = true
  kind                = "linux"

  sku {
    tier     = "PremiumV3"
    capacity = 1
    size     = "P1v3"
  }
}

resource "azurerm_app_service" "management_api" {
  name                = "api-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  app_service_plan_id = azurerm_app_service_plan.core.id
  https_only          = true

  app_settings = {
    "APPINSIGHTS_INSTRUMENTATIONKEY" = var.app_insights_instrumentation_key
    "WEBSITES_PORT"                  = "8000"
    "WEBSITE_VNET_ROUTE_ALL"         = 1

    "DOCKER_REGISTRY_SERVER_USERNAME"       = var.docker_registry_username
    "DOCKER_REGISTRY_SERVER_URL"            = "https://${var.docker_registry_server}"
    "DOCKER_REGISTRY_SERVER_PASSWORD"       = var.docker_registry_password
    "STATE_STORE_ENDPOINT"                  = var.state_store_endpoint
    "STATE_STORE_KEY"                       = var.state_store_key
    "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE" = "sb-${var.tre_id}.servicebus.windows.net"
    "SERVICE_BUS_RESOURCE_REQUEST_QUEUE"    = var.service_bus_resource_request_queue
    "SERVICE_BUS_DEPLOYMENT_STATUS_UPDATE_QUEUE" = var.service_bus_deployment_status_update_queue
    "MANAGED_IDENTITY_CLIENT_ID"            = var.managed_identity.client_id
    TRE_ID                                  = var.tre_id
    RESOURCE_LOCATION                       = var.location
  }

  identity {
    type = "UserAssigned"
    identity_ids = [ var.managed_identity.id ]
  }

  site_config {
    linux_fx_version            = "DOCKER|${var.docker_registry_server}/${var.management_api_image_repository}:${var.management_api_image_tag}"
    remote_debugging_enabled    = false
    scm_use_main_ip_restriction = true

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

resource "azurerm_private_endpoint" "management_api_private_endpoint" {
  name                = "pe-api-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.shared_subnet

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.management_api.id
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
  app_service_id = azurerm_app_service.management_api.id
  subnet_id      = var.web_app_subnet
}

resource "azurerm_monitor_diagnostic_setting" "webapp_management_api" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_app_service.management_api.id
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

output "management_api_fqdn" {
  value = azurerm_app_service.management_api.default_site_hostname
}
