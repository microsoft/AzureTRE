data "azurerm_client_config" "current" {
  provider = azurerm.core
}

data "azurerm_resource_group" "core" {
  provider = azurerm.core
  name     = "rg-${var.tre_id}"
}

data "azurerm_public_ip" "app_gateway_ip" {
  provider            = azurerm.core
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_storage_account" "stg" {
  name                = local.storage_name
  resource_group_name = local.ws_resource_group_name
}

data "azuread_user" "user" {
  count     = var.admin_username == "" ? 1 : 0
  object_id = var.owner_id
}
