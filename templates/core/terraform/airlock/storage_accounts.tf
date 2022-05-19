# 'External' storage account - drop location for import
resource "azurerm_storage_account" "sa_external_import" {
  name                     = local.airlock_external_import_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # Don't allow anonymous access (unrelated to the 'public' networking rules)
  allow_blob_public_access = false

  tags = {
    description = "airlock;import;external"
  }

  lifecycle { ignore_changes = [tags] }
}

# 'Accepted' export
resource "azurerm_storage_account" "sa_accepted_export" {
  name                     = local.airlock_accepted_export_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  # Don't allow anonymous access (unrelated to the 'public' networking rules)
  allow_blob_public_access = false

  tags = {
    description = "airlock;export;accepted"
  }

  lifecycle { ignore_changes = [tags] }
}

# 'In-Progress' storage account
resource "azurerm_storage_account" "sa_in_progress_import" {
  name                     = local.airlock_in_progress_import_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"
  allow_blob_public_access = false

  tags = {
    description = "airlock;import;in-progress"
  }

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_endpoint" "stg_ip_import_pe" {
  name                = "stgipimport-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-ip-import"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stgipimport-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_in_progress_import.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}


# 'Rejected' storage account
resource "azurerm_storage_account" "sa_rejected_import" {
  name                     = local.airlock_rejected_import_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"
  allow_blob_public_access = false

  tags = {
    description = "airlock;import;rejected"
  }

  network_rules {
    default_action             = var.enable_local_debugging ? "Allow" : "Deny"
    bypass                     = ["AzureServices"]
    virtual_network_subnet_ids = [var.shared_subnet_id]

  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "stgipimportpe" {
  name                = "stg-rej-import-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-rej-import"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-stg-rej-import-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_rejected_import.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}
