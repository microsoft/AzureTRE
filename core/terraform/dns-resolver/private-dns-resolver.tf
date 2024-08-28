# data "azurerm_virtual_network" "core_vnet" {
#   name                = local.core_vnet_name
#   resource_group_name = local.rg_name
# }

resource "azurerm_private_dns_resolver" "dns-resolver" {
  name                = "dns-resolver"
  resource_group_name = var.resource_group_name
  location            = var.location
  virtual_network_id  = var.core_vnet_id
}

resource "azurerm_private_dns_resolver_outbound_endpoint" "dns-resolver-outbound" {
  name                    = "dns-resolver-outbound-endpoint"
  private_dns_resolver_id = azurerm_private_dns_resolver.dns-resolver.id
  location                = azurerm_private_dns_resolver.dns-resolver.location
  subnet_id               = azurerm_subnet.dns-snet-outbound.id
}
