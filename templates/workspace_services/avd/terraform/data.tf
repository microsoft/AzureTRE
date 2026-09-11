data "azurerm_client_config" "current" {
  provider = azurerm.core
}

data "azurerm_user_assigned_identity" "resource_processor_vmss_id" {
  provider            = azurerm.core
  name                = "id-vmss-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_key_vault_secret" "aad_tenant_id" {
  name         = "auth-tenant-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "azuread_service_principal" "avd" {
  count     = var.host_pool_type == "Pooled" ? 1 : 0
  client_id = "9cdead84-a844-4324-93f2-b2e6bb768d07"
}

data "azurerm_storage_account" "stg" {
  name                = local.storage_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_log_analytics_workspace" "tre" {
  provider            = azurerm.core
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "wvd" {
  provider            = azurerm.core
  name                = local.wvd_private_dns_zone_name
  resource_group_name = local.core_resource_group_name
}

data "azapi_resource" "avd_workspace" {
  type                   = "Microsoft.DesktopVirtualization/workspaces@2023-09-05"
  resource_id            = azurerm_virtual_desktop_workspace.avd.id
  response_export_values = ["properties.objectId"]
}

data "azapi_resource_list" "desktops" {
  type      = "Microsoft.DesktopVirtualization/applicationGroups/desktops@2023-09-05"
  parent_id = azurerm_virtual_desktop_application_group.avd.id
  response_export_values = {
    object_ids = "value[].properties.objectId"
  }
}
