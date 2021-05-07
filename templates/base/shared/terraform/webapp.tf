resource "azurerm_app_service_plan" "core" {

  name                = "asp-core"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.location
  reserved            = true
  kind                = "linux"
  sku {
    tier     = "PremiumV3"
    capacity = 1
    size     = "P1v3"
  }
}

resource "azurerm_application_insights" "core" {
  name                = "ai-core"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.location
  application_type    = "web"

}
resource "azurerm_app_service" "management_api" {

  name                = "webapp-management-api-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.location
  app_service_plan_id = azurerm_app_service_plan.core.id

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.management_api.id]
  }

  https_only = true
  app_settings = {

    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.core.instrumentation_key

    "DOCKER_REGISTRY_SERVER_USERNAME" = var.container_registry_username
    "DOCKER_REGISTRY_SERVER_URL"      = "https://${var.container_registry_dns_name}"
    "DOCKER_REGISTRY_SERVER_PASSWORD" = var.container_registry_password

  }
  site_config {
    linux_fx_version            = "DOCKER|${local.management_api_image_name}"
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


resource "azurerm_user_assigned_identity" "management_api" {
  name =  "msi-management-api"
  resource_group_name = azurerm_resource_group.core.name
  location = azurerm_resource_group.core.location
}

resource "azurerm_private_endpoint" "management_api_private_endpoint" {
  name                = "pe-management-api"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  subnet_id           = azurerm_subnet.private_endpoints.id
  private_service_connection {
    private_connection_resource_id = azurerm_app_service.management_api.id
    name                           = "pe-webapp-management-api"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [azurerm_private_dns_zone.azurewebsites.id]
  }
}


resource "azurerm_private_dns_zone" "azurewebsites" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = azurerm_resource_group.core.name

}

resource "azurerm_private_dns_zone_virtual_network_link" "azurewebsites" {
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.azurewebsites.name
  name                  = "azurewebsites-link"
  registration_enabled  = false


}
resource "azurerm_monitor_diagnostic_setting" "webapp_management_api" {
  name                       = "diagnostics-webapp-shared-api"
  target_resource_id         = azurerm_app_service.management_api.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.tre.id

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