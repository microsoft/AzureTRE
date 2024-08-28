# resource "azurerm_private_dns_resolver_virtual_network_link" "tony-dns-link" {
#   name                      = "tony-dns-link"
#   dns_forwarding_ruleset_id = azurerm_private_dns_resolver_dns_forwarding_ruleset.tony-dns-ruleset.id
#   virtual_network_id        = azurerm_virtual_network.tony-vm-vnet.id
# }

# data "azurerm_virtual_network" "ws_vnet" {
#   name                = local.ws_vnet_name
#   resource_group_name = local.ws_vnet_rg_name
# }

# resource "azurerm_private_dns_resolver_virtual_network_link" "tony-dns-ws-link" {
#   name                      = "tony-dns-ws-link"
#   dns_forwarding_ruleset_id = azurerm_private_dns_resolver_dns_forwarding_ruleset.tony-dns-ruleset.id
#   virtual_network_id        = data.azurerm_virtual_network.ws_vnet.id
# }
