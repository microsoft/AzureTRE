data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${var.workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${var.workspace_id}"
  resource_group_name = "rg-${var.tre_id}-ws-${var.workspace_id}"
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

resource "azurerm_storage_account" "stg" {
  name                     = local.storage_name
  resource_group_name      = data.azurerm_resource_group.ws.name
  location                 = data.azurerm_resource_group.ws.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  lifecycle { ignore_changes = [ tags ] }

  network_rules {
      bypass         = ["AzureServices"]
      default_action = "Deny"
  }
}

resource "azurerm_private_dns_zone" "filecore" {
  name                = "privatelink.file.core.windows.net"
  resource_group_name = data.azurerm_resource_group.ws.name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = data.azurerm_resource_group.ws.name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "filecorelink" {
  name                  = "filecorelink-${local.service_resource_name_suffix}"
  resource_group_name   = data.azurerm_resource_group.ws.name
  private_dns_zone_name = azurerm_private_dns_zone.filecore.name
  virtual_network_id    = data.azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcorelink" {
  name                  = "blobcorelink-${local.service_resource_name_suffix}"
  resource_group_name   = data.azurerm_resource_group.ws.name
  private_dns_zone_name = azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = data.azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_endpoint" "stgfilepe" {
  name                = "stgfilepe-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  lifecycle { ignore_changes = [ tags ] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.filecore.id]
  }

  private_service_connection {
    name                           = "stgfilepesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["File"]
  }
}

resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "stgblobpe-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  lifecycle { ignore_changes = [ tags ] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "stgblobpesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}
