data "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_virtual_network" "core" {
  name                = local.core_vnet
  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "shared" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "SharedSubnet"
}

data "azurerm_firewall" "fw" {
  name                = "fw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_key_vault" "kv" {
  name                = "kv-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_storage_account" "nexus" {
  name                = local.storage_account_name
  resource_group_name = local.core_resource_group_name
}
