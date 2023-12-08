# we have to use user-assigned to break a cycle in the dependencies: app identity, kv-policy, secrets in app settings
resource "azurerm_user_assigned_identity" "rshiny_id" {
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  tags                = local.workspace_service_tags

  name = "id-rshiny-${local.service_resource_name_suffix}"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_linux_web_app" "rshiny" {
  name                            = local.webapp_name
  location                        = data.azurerm_resource_group.ws.location
  resource_group_name             = data.azurerm_resource_group.ws.name
  service_plan_id                 = data.azurerm_service_plan.workspace.id
  https_only                      = true
  key_vault_reference_identity_id = azurerm_user_assigned_identity.rshiny_id.id
  virtual_network_subnet_id       = data.azurerm_subnet.web_apps.id
  tags                            = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.rshiny_id.id]
  }

  site_config {
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.rshiny_id.client_id
    ftps_state                                    = "Disabled"
    always_on                                     = true
    minimum_tls_version                           = "1.2"
    vnet_route_all_enabled                        = true

    application_stack {
      docker_image_name = "${data.azurerm_container_registry.mgmt_acr.login_server}/microsoft/azuretre/rshiny-workspace-service:${local.version}"
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

resource "azurerm_private_endpoint" "rshiny_private_endpoint" {
  name                = "pe-${local.webapp_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.rshiny.id
    name                           = "psc-${local.webapp_name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_diagnostic_setting" "rshiny" {
  name                       = "diag-${local.service_resource_name_suffix}"
  target_resource_id         = azurerm_linux_web_app.rshiny.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  dynamic "log" {
    for_each = data.azurerm_monitor_diagnostic_categories.rshiny.log_category_types
    content {
      category = log.value
      enabled  = contains(local.web_app_diagnostic_categories_enabled, log.value) ? true : false
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "azurerm_role_assignment" "rshiny_acrpull_role" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.rshiny_id.principal_id
}
