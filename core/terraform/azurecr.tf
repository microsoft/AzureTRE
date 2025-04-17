resource "azurerm_private_endpoint" "acrpe" {
  count               = var.disable_acr_public_access ? 1 : 0
  name                = "pe-${data.azurerm_container_registry.mgmt_acr.name}-${var.tre_id}"
  location            = var.location
  resource_group_name = var.mgmt_resource_group_name
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

  depends_on = [
    azurerm_private_endpoint.sbpe
  ]
}