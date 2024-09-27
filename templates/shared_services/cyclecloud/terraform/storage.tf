resource "azurerm_storage_account" "cyclecloud" {
  name                     = local.storage_name
  location                 = data.azurerm_resource_group.rg.location
  resource_group_name      = data.azurerm_resource_group.rg.name
  account_tier             = "Standard"
  account_replication_type = "GRS"
  tags                     = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "pe-${local.storage_name}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = data.azurerm_subnet.shared.id
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "pesc-${local.storage_name}"
    private_connection_resource_id = azurerm_storage_account.cyclecloud.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}
