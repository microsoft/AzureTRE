resource "azurerm_storage_share" "atlas_ui" {
  name                 = local.atlas_ui_storage_share_name
  storage_account_name = data.azurerm_storage_account.stg.name
  quota                = 1
}

resource "local_file" "config_local" {
  content  = templatefile("${path.module}/config_local.tftpl", { OHDSI_WEBAPI_URL = local.ohdsi_webapi_url })
  filename = local.config_local_file_path
}

resource "azurerm_storage_share_file" "config_local" {
  name             = "config-local.js"
  storage_share_id = azurerm_storage_share.atlas_ui.id
  source           = local.config_local_file_path

  depends_on = [
    local_file.config_local
  ]
}

resource "azurerm_linux_web_app" "atlas_ui" {
  name                      = local.atlas_ui_name
  location                  = data.azurerm_resource_group.ws.location
  resource_group_name       = data.azurerm_resource_group.ws.name
  virtual_network_subnet_id = data.azurerm_subnet.web_app.id

  service_plan_id         = data.azurerm_service_plan.workspace.id
  https_only              = true
  client_affinity_enabled = false

  site_config {
    always_on           = false
    ftps_state          = "Disabled"
    minimum_tls_version = "1.3"

    application_stack {
      docker_image_name = "index.docker.io/${local.atlas_ui_docker_image_name}:${local.atlas_ui_docker_image_tag}"
    }
  }

  storage_account {
    access_key   = data.azurerm_storage_account.stg.primary_access_key
    account_name = data.azurerm_storage_account.stg.name
    name         = "ui-storage-${local.service_suffix}"
    share_name   = local.atlas_ui_storage_share_name
    type         = "AzureFiles"
    mount_path   = local.atlas_ui_mount_path
  }

  app_settings = {
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = false
    WEBSITES_PORT                       = "8080"
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
    azurerm_storage_share_file.config_local,
  ]

  tags = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "atlas_ui_private_endpoint" {
  name                = "pe-${azurerm_linux_web_app.atlas_ui.name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.atlas_ui.id
    name                           = "psc-${azurerm_linux_web_app.atlas_ui.name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_diagnostic_setting" "atlas_ui" {
  name                       = azurerm_linux_web_app.atlas_ui.name
  target_resource_id         = azurerm_linux_web_app.atlas_ui.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.workspace.id

  dynamic "enabled_log" {
    for_each = local.atals_ui_log_analytics_categories
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
