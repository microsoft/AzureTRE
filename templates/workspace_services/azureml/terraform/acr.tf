

resource "azurerm_container_registry" "acr" {
  name                          = local.acr_name
  location                      = data.azurerm_resource_group.ws.location
  resource_group_name           = data.azurerm_resource_group.ws.name
  sku                           = "Premium"
  admin_enabled                 = false
  public_network_access_enabled = false
  tags                          = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "azurecr" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurecr.io"]
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_endpoint" "acrpe" {
  name                = "acrpe-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = azurerm_subnet.aml.id
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurecr.id]
  }

  private_service_connection {
    name                           = "acrpesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_container_registry.acr.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }

}

