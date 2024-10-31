resource "azurerm_storage_account" "stg" {
  name                             = lower(replace("stg-${var.tre_id}", "-", ""))
  resource_group_name              = azurerm_resource_group.core.name
  location                         = azurerm_resource_group.core.location
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  tags                             = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_share" "storage_state_path" {
  name                 = "cnab-state"
  storage_account_name = azurerm_storage_account.stg.name
  quota                = 50
}

resource "azurerm_private_endpoint" "blobpe" {
  name                = "pe-blob-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.shared_subnet_id
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-blobcore"
    private_dns_zone_ids = [module.network.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }

  # private endpoints in serial
  depends_on = [
    azurerm_private_endpoint.kvpe
  ]
}

resource "azurerm_private_endpoint" "filepe" {
  name                = "pe-file-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.shared_subnet_id
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-filecore"
    private_dns_zone_ids = [module.network.file_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-filestg-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["file"]
  }

  # private endpoints in serial
  depends_on = [
    azurerm_private_endpoint.blobpe
  ]
}
