data "azurerm_resource_group" "core" {
  name = local.core_resource_group_name
}

data "azurerm_user_assigned_identity" "agw" {
  name                = "id-agw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "agw_int" {
  name                 = "AppGwInternalSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_key_vault" "core" {
  name                = "kv-tktre01"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_key_vault_secrets" "secrets" {
  key_vault_id = data.azurerm_key_vault.core.id
}
