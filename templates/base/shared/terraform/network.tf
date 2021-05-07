resource "azurerm_virtual_network" "core" {
  name                = "vnet-core"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  address_space       = [var.shared_services_vnet_address_space]
}

resource "azurerm_subnet" "bastion" {
  name                 = "AzureBastionSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = azurerm_resource_group.core.name
  address_prefixes     = [local.bastion_subnet_address_prefix]

}

resource "azurerm_subnet" "azure_firewall" {
  name                 = "AzureFirewallSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = azurerm_resource_group.core.name
  address_prefixes     = [local.firewall_subnet_address_space]
}

resource "azurerm_subnet" "app_gw" {
  name                 = "appGwSubnet"
  virtual_network_name = azurerm_virtual_network.core.name
  resource_group_name  = azurerm_resource_group.core.name
  address_prefixes     = [local.app_gw_subnet_address_prefix]
}

resource "azurerm_subnet" "private_endpoints" {
  name                                           = "privateEndpointSubnet"
  virtual_network_name                           = azurerm_virtual_network.core.name
  resource_group_name                            = azurerm_resource_group.core.name
  address_prefixes                               = [local.web_app_subnet_address_prefix]
  enforce_private_link_endpoint_network_policies = true
}

resource "azurerm_subnet" "shared_services" {
  name                                           = "sharedServicesSubnet"
  virtual_network_name                           = azurerm_virtual_network.core.name
  resource_group_name                            = azurerm_resource_group.core.name
  address_prefixes                               = [local.shared_services_subnet_address_prefix]
  enforce_private_link_endpoint_network_policies = true
}