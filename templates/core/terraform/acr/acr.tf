
locals {
    acr_name        = lower(replace("acr${var.tre_id}","-",""))
}

resource "azurerm_container_registry" "acr" {
  name                     = local.acr_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  sku                      = "Premium"
  admin_enabled            = false

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone" "azurecr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "acrlink" {
  name                  = "acr-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = var.core_vnet
  
  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_endpoint" "acrpe" {
  name                = "pe-acr-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.azurecr.id]
  }

  private_service_connection {
    name                           = "psc-acr-${var.tre_id}"
    private_connection_resource_id = azurerm_container_registry.acr.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }

  lifecycle { ignore_changes = [ tags ] }
}
