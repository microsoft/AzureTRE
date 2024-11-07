# the zones defined in this file aren't used by the core system,
# but are a preperation for shared/workspace services deployment.

resource "azurerm_private_dns_zone" "non_core" {
  for_each            = local.private_dns_zone_names_non_core
  name                = module.terraform_azurerm_environment_configuration.private_links[each.key]
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

# since shared services are in the core network, their dns link could exist once and must be defined here.
resource "azurerm_private_dns_zone_virtual_network_link" "azuresql" {
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = module.network.core_vnet_id
  private_dns_zone_name = azurerm_private_dns_zone.non_core["privatelink.database.windows.net"].name
  name                  = azurerm_private_dns_zone.non_core["privatelink.database.windows.net"].name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "openai" {
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = module.network.core_vnet_id
  private_dns_zone_name = azurerm_private_dns_zone.non_core["privatelink.openai.azure.com"].name
  name                  = azurerm_private_dns_zone.non_core["privatelink.openai.azure.com"].name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "cognitivesearch" {
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = module.network.core_vnet_id
  private_dns_zone_name = azurerm_private_dns_zone.non_core["privatelink.cognitiveservices.azure.com"].name
  name                  = azurerm_private_dns_zone.non_core["privatelink.cognitiveservices.azure.com"].name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

# Once the deployment of the app gateway is complete, we can proceed to include the required DNS zone for Nexus, which is dependent on the FQDN of the app gateway.
resource "azurerm_private_dns_zone" "nexus" {
  name                = "nexus-${module.appgateway.app_gateway_fqdn}"
  resource_group_name = azurerm_resource_group.core.name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}
