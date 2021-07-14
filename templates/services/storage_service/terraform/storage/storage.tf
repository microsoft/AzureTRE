resource "azurerm_storage_account" "storage" {
  name                     = local.storage_name
  resource_group_name      = local.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  network_rules {
      bypass         = ["AzureServices"]
      default_action = "Deny"
  }
}

resource "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = local.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcorelink" {
  name                  = "blobcorelink"
  resource_group_name   = local.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = data.azurerm_virtual_network.ws.id
}

resource "azurerm_private_endpoint" "blobpe" {
  name                = "pe-stg-${local.storage_name}"
  location            = var.location
  resource_group_name = local.resource_group_name
  subnet_id           = data.azurerm_subnet.ServicesSubnet.id

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stg-local.storage_name"
    private_connection_resource_id = azurerm_storage_account.storage.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}