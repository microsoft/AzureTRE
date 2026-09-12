data "azurerm_client_config" "current" {
  provider = azurerm.core
}

data "azurerm_user_assigned_identity" "resource_processor_vmss_id" {
  provider            = azurerm.core
  name                = "id-vmss-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_resource_group" "core" {
  provider = azurerm.core
  name     = "rg-${var.tre_id}"
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

data "azurerm_key_vault_secret" "avd_registration_token" {
  name         = "avd-registration-token-${local.short_parent_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
  depends_on   = [terraform_data.avd_registration]
}

data "azurerm_key_vault_secret" "clipboard_transfer_direction" {
  name         = "avd-clipboard-direction-${local.short_parent_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "azurerm_key_vault_secret" "aad_tenant_id" {
  name         = "auth-tenant-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "azuread_user" "owner" {
  object_id = var.owner_id
}

data "azuread_service_principal" "avd" {
  client_id = "9cdead84-a844-4324-93f2-b2e6bb768d07"
}

data "azurerm_virtual_desktop_host_pool" "avd" {
  name                = "vdpool-${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_parent_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azapi_resource" "avd_workspace" {
  type                   = "Microsoft.DesktopVirtualization/workspaces@2024-04-03"
  name                   = "vdws-${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_parent_id}"
  parent_id              = data.azurerm_resource_group.ws.id
  response_export_values = ["properties.objectId"]
}

data "azapi_resource" "avd_desktop" {
  type                   = "Microsoft.DesktopVirtualization/applicationGroups/desktops@2024-04-03"
  name                   = "SessionDesktop"
  parent_id              = "${data.azurerm_resource_group.ws.id}/providers/Microsoft.DesktopVirtualization/applicationGroups/vdag-${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_parent_id}"
  response_export_values = ["properties.objectId"]
}

data "azapi_resource" "avd_session_host" {
  type                   = "Microsoft.DesktopVirtualization/hostPools/sessionHosts@2024-04-03"
  resource_id            = azapi_resource_action.session_host_assignment.resource_id
  response_export_values = ["properties.objectId"]

  depends_on = [azapi_resource_action.session_host_assignment]
}

data "azurerm_storage_account" "stg" {
  name                = local.storage_name
  resource_group_name = data.azurerm_resource_group.ws.name
}
