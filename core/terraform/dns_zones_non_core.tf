# the zones defined in this file aren't used by the core system,
# but are a preperation for shared/workspace services deployment.

resource "azurerm_private_dns_zone" "non_core" {
  for_each            = local.private_dns_zone_names_non_core
  name                = each.key
  resource_group_name = azurerm_resource_group.core.name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

# since shared services are in the core network, their dns link could exist once and must be defined here.
resource "azurerm_private_dns_zone_virtual_network_link" "mysql" {
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = module.network.core_vnet_id
  private_dns_zone_name = azurerm_private_dns_zone.non_core["privatelink.mysql.database.azure.com"].name
  name                  = azurerm_private_dns_zone.non_core["privatelink.mysql.database.azure.com"].name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}
