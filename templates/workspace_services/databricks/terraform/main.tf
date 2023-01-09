data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "rg" {
  name = local.resource_group_name
}

data "azurerm_virtual_network" "ws" {
  name                = local.virtual_network_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_key_vault" "kv" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_firewall" "firewall" {
  name                = local.firewall_name
  resource_group_name = local.core_resource_group_name
}

data "azurerm_public_ip" "firewall-public-ip" {
  name                = reverse(split("/", data.azurerm_firewall.firewall.ip_configuration.0.public_ip_address_id))[0]
  resource_group_name = local.core_resource_group_name
}
