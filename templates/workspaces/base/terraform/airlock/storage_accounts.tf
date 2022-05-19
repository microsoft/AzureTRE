# 'Accepted' storage account
resource "azurerm_storage_account" "sa_accepted_import" {
  name                            = local.airlock_accepted_import_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  allow_nested_items_to_be_public = false

  tags = {
    description = "airlock;import;accepted"
  }

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_endpoint" "stg_acc_import_pe" {
  name                = "stg-acc-import-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-acc-import"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stg-acc-import-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_accepted_import.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}


# 'Drop' location for export
resource "azurerm_storage_account" "sa_internal_export" {
  name                            = local.airlock_internal_export_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  allow_nested_items_to_be_public = false

  tags = {
    description = "airlock;export;internal"
  }

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_endpoint" "stg_int_export_pe" {
  name                = "stg-int-export-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-int-export"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stg-int-export-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_internal_export.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'In-progress' location for export
resource "azurerm_storage_account" "sa_inprogress_export" {
  name                            = local.airlock_inprogress_export_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  allow_nested_items_to_be_public = false

  tags = {
    description = "airlock;export;inprogress"
  }

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_endpoint" "stg_ip_export_pe" {
  name                = "stg-ip-export-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-ip-export"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stg-ip-export-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_inprogress_export.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'Rejected' location for export
resource "azurerm_storage_account" "sa_rejected_export" {
  name                            = local.airlock_rejected_export_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  allow_nested_items_to_be_public = false

  tags = {
    description = "airlock;export;rejected"
  }

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_endpoint" "stg_rej_export_pe" {
  name                = "stg-rej-export-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-rej-export"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stg-rej-export-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_rejected_export.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}
