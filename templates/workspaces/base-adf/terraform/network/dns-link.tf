data "azurerm_private_dns_resolver_dns_forwarding_ruleset" "core-dns-ruleset" {
  name                = "dns-ruleset"
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_dns_resolver_virtual_network_link" "dns-ws-link" {
  name                      = "dns-ws-link-${local.workspace_resource_name_suffix}"
  # dns_forwarding_ruleset_id = azurerm_private_dns_resolver_dns_forwarding_ruleset.tony-dns-ruleset.id
  dns_forwarding_ruleset_id = data.azurerm_private_dns_resolver_dns_forwarding_ruleset.core-dns-ruleset.id
  virtual_network_id        = azurerm_virtual_network.ws.id
}
