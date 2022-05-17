resource "random_password" "HUE_passwd" {
  length      = 20
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
}

# we have to use user-assigned to break a cycle in the dependencies: app identity, kv-policy, secrets in app settings
resource "azurerm_user_assigned_identity" "HUE_id" {
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location

  name = "id-HUE-${local.service_resource_name_suffix}"

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_app_service_plan" "workspace" {
  name                = "plan-${var.workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

resource "azurerm_app_service" "HUE" {
  name                            = local.webapp_name
  location                        = data.azurerm_resource_group.ws.location
  resource_group_name             = data.azurerm_resource_group.ws.name
  app_service_plan_id             = data.azurerm_app_service_plan.workspace.id
  https_only                      = true

  app_settings = {
    WEBSITES_PORT                                    = "8888"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE              = true
    WEBSITE_DNS_SERVER                               = "168.63.129.16"
    HUE_USERNAME                                   = "HUEadmin"
    HUE_PASSWD                                     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.HUE_password.id})"
    HUE_EMAIL                                      = "HUEadmin@azuretre.com"
    HUE__server__ROOT_URL                          = "https://${local.webapp_name}.azurewebsites.net/"
  }

  lifecycle { ignore_changes = [tags] }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.HUE_id.id]
  }

  site_config {
    linux_fx_version                     = "DOCKER|gethue/hue-latest"
    always_on                            = true
    min_tls_version                      = "1.2"
    vnet_route_all_enabled               = true
    websockets_enabled                   = false
  }

  # storage_account {
  #   name         = local.workspace_storage_name
  #   type         = "AzureFiles"
  #   account_name = azurerm_storage_account.HUE.name
  #   access_key   = azurerm_storage_account.HUE.primary_access_key
  #   share_name   = azurerm_storage_share.HUE.name
  #   mount_path   = "/data/HUE/"
  # }

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

resource "azurerm_private_endpoint" "HUE_private_endpoint" {
  name                = "pe-${local.webapp_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  private_service_connection {
    private_connection_resource_id = azurerm_app_service.HUE.id
    name                           = "psc-${local.webapp_name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.azurewebsites.net"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_app_service_virtual_network_swift_connection" "HUE-integrated-vnet" {
  app_service_id = azurerm_app_service.HUE.id
  subnet_id      = data.azurerm_subnet.web_apps.id
}

resource "azurerm_monitor_diagnostic_setting" "webapp_HUE" {
  name                       = "diag-${local.service_resource_name_suffix}"
  target_resource_id         = azurerm_app_service.HUE.id
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

resource "azurerm_key_vault_access_policy" "HUE_policy" {
  key_vault_id = data.azurerm_key_vault.ws.id
  tenant_id    = azurerm_user_assigned_identity.HUE_id.tenant_id
  object_id    = azurerm_user_assigned_identity.HUE_id.principal_id

  secret_permissions = ["Get", "List", ]
}

resource "azurerm_key_vault_secret" "HUE_password" {
  name         = "${local.webapp_name}-administrator-password"
  value        = random_password.HUE_passwd.result
  key_vault_id = data.azurerm_key_vault.ws.id

  depends_on = [
    azurerm_key_vault_access_policy.HUE_policy
  ]
}
