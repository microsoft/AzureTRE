data "azurerm_subnet" "firewall" {
  name                 = "AzureFirewallSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = var.resource_group_name
}

data "azurerm_subnet" "shared" {
  name                 = "SharedSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = var.resource_group_name
}

data "azurerm_subnet" "resource_processor" {
  name                 = "ResourceProcessorSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = var.resource_group_name
}
