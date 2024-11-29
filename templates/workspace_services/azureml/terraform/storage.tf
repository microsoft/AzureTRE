resource "azurerm_storage_account" "aml" {
  name                             = local.storage_name
  location                         = data.azurerm_resource_group.ws.location
  resource_group_name              = data.azurerm_resource_group.ws.name
  account_tier                     = "Standard"
  account_replication_type         = "GRS"
  cross_tenant_replication_enabled = false
  tags                             = local.tre_workspace_service_tags
  network_rules {
    default_action = "Deny"
  }

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "filecore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.file.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_endpoint" "blobpe" {
  name                = "pe-${local.storage_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = azurerm_subnet.aml.id
  tags                = local.tre_workspace_service_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "dnsgroup-blob${local.storage_name}"
    private_connection_resource_id = azurerm_storage_account.aml.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }


}


resource "azurerm_private_endpoint" "filepe" {
  name                = "pe-file-${local.storage_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = azurerm_subnet.aml.id
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "dnsgroup-files-${local.storage_name}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.filecore.id]
  }

  private_service_connection {
    name                           = "dnsgroup-file-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.aml.id
    is_manual_connection           = false
    subresource_names              = ["file"]
  }

  depends_on = [
    azurerm_private_endpoint.blobpe
  ]

}
