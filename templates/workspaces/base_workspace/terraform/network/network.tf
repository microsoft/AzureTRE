resource "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.address_space]
}


resource "azurerm_subnet" "services" {
  name                                           = "ServicesSubnet"
  virtual_network_name                           = azurerm_virtual_network.ws.name
  resource_group_name                            = var.resource_group_name
  address_prefixes                               = [local.services_subnet_address_prefix]
  enforce_private_link_endpoint_network_policies = true
}

data "azurerm_virtual_network" "core" {
  name                = var.core_vnet
  resource_group_name = var.core_resource_group_name
}

resource "azurerm_virtual_network_peering" "ws-core-peer" {
  name                      = "ws-core-peer-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name       = var.resource_group_name
  virtual_network_name      = azurerm_virtual_network.ws.name
  remote_virtual_network_id = data.azurerm_virtual_network.core.id
}

resource "azurerm_virtual_network_peering" "core-ws-peer" {
  name                      = "core-ws-peer-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name       = var.core_resource_group_name
  virtual_network_name      = var.core_vnet
  remote_virtual_network_id = azurerm_virtual_network.ws.id
}
