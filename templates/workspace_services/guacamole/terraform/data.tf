data "azurerm_client_config" "current" {
  provider = azurerm.core
}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_key_vault_secret" "aad_tenant_id" {
  name         = "auth-tenant-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "azurerm_key_vault_secret" "workspace_client_id" {
  name         = "workspace-client-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "azurerm_key_vault_secret" "workspace_client_secret" {
  name         = "workspace-client-secret"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "azurerm_subnet" "web_apps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
}

data "azurerm_private_dns_zone" "azurewebsites" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_container_registry" "mgmt_acr" {
  provider            = azurerm.core
  name                = var.mgmt_acr_name
  resource_group_name = var.mgmt_resource_group_name
}

data "azurerm_log_analytics_workspace" "tre" {
  provider            = azurerm.core
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "local_file" "version" {
  filename = "${path.module}/../guacamole-server/docker/version.txt"
}

data "azurerm_application_insights" "ws" {
  name                = "appi-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_monitor_diagnostic_categories" "guacamole" {
  resource_id = azurerm_linux_web_app.guacamole.id
  depends_on = [
    azurerm_linux_web_app.guacamole,
  ]
}

data "azurerm_service_plan" "workspace" {
  name                = "plan-${var.workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}
