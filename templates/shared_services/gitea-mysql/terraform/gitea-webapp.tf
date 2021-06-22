resource "azurerm_app_service" "gitea" {
  name                = "gitea-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = var.location
  app_service_plan_id = data.azurerm_app_service_plan.core.id
  https_only          = true

  app_settings = {
    "APPINSIGHTS_INSTRUMENTATIONKEY" = data.azurerm_application_insights.core.instrumentation_key
    "WEBSITES_PORT"                  = "3000"
    "WEBSITE_VNET_ROUTE_ALL"         = 1

    TRE_ID            = var.tre_id
    RESOURCE_LOCATION = var.location

    WEBSITES_ENABLE_APP_SERVICE_STORAGE = true

    GITEA__server__APP_DATA_PATH="/home/data"
    GITEA__server__ROOT_URL="https://gitea-${var.tre_id}.azurewebsites.net/"

    GITEA__repository__ROOT="/home/data/git/gitea-repositories"

    # SSL disabled see task: #347 
    GITEA__database__SSL_MODE="disable"
    GITEA__database__DB_TYPE="mysql"
    GITEA__database__HOST=azurerm_mysql_server.gitea.fqdn
    GITEA__database__NAME="gitea"
    GITEA__database__USER="mysqladmin@${azurerm_mysql_server.gitea.fqdn}"
    GITEA__database__PASSWD=random_password.password.result
    
    GITEA__security__INSTALL_LOCK=true
  }

  site_config {
    linux_fx_version            = "DOCKER|gitea/gitea"
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

resource "azurerm_private_endpoint" "gitea_private_endpoint" {
  name                = "pe-gitea-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
  location            = var.location
  subnet_id           = data.azurerm_subnet.shared.id

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.gitea.id
    name                           = "psc-gitea-${var.tre_id}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }
}

resource "azurerm_app_service_virtual_network_swift_connection" "gitea-integrated-vnet" {
  app_service_id = azurerm_app_service.gitea.id
  subnet_id      = data.azurerm_subnet.web_app.id
}

resource "azurerm_monitor_diagnostic_setting" "webapp_gitea" {
  name                       = "diag-${var.tre_id}"
  target_resource_id         = azurerm_app_service.gitea.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

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

output "gitea_fqdn" {
  value = azurerm_app_service.gitea.default_site_hostname
}
