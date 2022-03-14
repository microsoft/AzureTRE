resource "azurerm_storage_account" "stg" {
  name                     = local.storage_name
  resource_group_name      = azurerm_resource_group.ws.name
  location                 = azurerm_resource_group.ws.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_share" "shared_storage" {
  name                 = "vm-shared-storage"
  storage_account_name = azurerm_storage_account.stg.name
  quota                = var.shared_storage_quota

  depends_on = [
    azurerm_private_endpoint.stgfilepe
  ]
}

resource "azurerm_storage_account_network_rules" "stgrules" {
  resource_group_name  = azurerm_resource_group.ws.name
  storage_account_name = azurerm_storage_account.stg.name

  default_action = "Deny"
  bypass         = ["AzureServices"]
}

resource "azurerm_private_endpoint" "stgfilepe" {
  name                = "stgfilepe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = azurerm_subnet.services.id

  depends_on = [
    azurerm_subnet.services
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.filecore.id]
  }

  private_service_connection {
    name                           = "stgfilepesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["File"]
  }
}


resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "stgblobpe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = azurerm_subnet.services.id

  depends_on = [
    azurerm_subnet.services
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "stgblobpesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}
