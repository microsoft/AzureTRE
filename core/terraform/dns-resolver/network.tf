# # Virtual Network for DNS
# resource "azurerm_virtual_network" "dns-vnet" {
#   name                = "dns-vnet"
#   address_space       = [ local.core_address_space ]
#   location            = local.location
#   resource_group_name = local.rg_name
# }

# resource "azurerm_subnet" "dns-snet-inbound" {
#   name                 = "dns-snet-inbound"
#   resource_group_name = local.rg_name
#   virtual_network_name = azurerm_virtual_network.dns-vnet.name
#   address_prefixes     = [ local.core_services_vnet_subnets[11] ]
#   delegation {
#     name = "Microsoft.Network.dnsResolvers"
#     service_delegation {
#       actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
#       name    = "Microsoft.Network/dnsResolvers"
#     }
#   }
# }

resource "azurerm_subnet" "dns-snet-outbound" {
  name                 = "AzurePrivateDnsResolverSubnet"
  resource_group_name = var.resource_group_name
  virtual_network_name = var.core_vnet_name
  address_prefixes     = [ local.dns_resolver_subnet_address_prefix ]
  delegation {
    name = "Microsoft.Network.dnsResolvers"
    service_delegation {
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
      name    = "Microsoft.Network/dnsResolvers"
    }
  }
}
