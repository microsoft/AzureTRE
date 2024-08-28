resource "azurerm_private_dns_resolver_dns_forwarding_ruleset" "dns-ruleset" {
  name                                       = "dns-ruleset"
  resource_group_name                        = var.resource_group_name
  location                                   = var.location
  private_dns_resolver_outbound_endpoint_ids = [ azurerm_private_dns_resolver_outbound_endpoint.dns-resolver-outbound.id ]
}
