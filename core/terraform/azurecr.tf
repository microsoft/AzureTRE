resource "azurerm_private_endpoint" "acrpe" {
  name                = "pe-${data.azurerm_container_registry.mgmt_acr.name}-${var.tre_id}"
  location            = var.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.shared_subnet_id
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-acr"
    private_dns_zone_ids = [module.network.azurecr_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-${data.azurerm_container_registry.mgmt_acr.name}-${var.tre_id}"
    private_connection_resource_id = data.azurerm_container_registry.mgmt_acr.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }
}
