data "azurerm_client_config" "current" {
  provider = azurerm.core
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

data "azurerm_linux_web_app" "guacamole" {
  name                = "guacamole-${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_parent_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_public_ip" "app_gateway_ip" {
  provider            = azurerm.core
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_storage_account" "stg" {
  name                = local.storage_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_key_vault_key" "ws_encryption_key" {
  count        = var.enable_cmk_encryption ? 1 : 0
  name         = local.cmk_name
  key_vault_id = var.key_store_id
}

data "azurerm_user_assigned_identity" "ws_encryption_identity" {
  count               = var.enable_cmk_encryption ? 1 : 0
  name                = local.encryption_identity_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azuread_user" "user" {
  count     = var.admin_username == "" ? 1 : 0
  object_id = var.owner_id
}
