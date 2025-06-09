# 'External' storage account - drop location for import
resource "azurerm_storage_account" "sa_import_external" {
  name                     = local.import_external_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "LRS"
  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["DELETE", "GET", "HEAD", "MERGE", "POST", "OPTIONS", "PUT"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 86400
    }
  }
  # Don't allow anonymous access (unrelated to the 'public' networking rules)
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;external"
  })

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "stg_import_external_pe" {
  name                = "stg-ex-import-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-export-app"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stgeximport-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_external.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'Approved' export
resource "azurerm_storage_account" "sa_export_approved" {
  name                     = local.export_approved_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Don't allow anonymous access (unrelated to the 'public' networking rules)
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  tags = merge(var.tre_core_tags, {
    description = "airlock;export;approved"
  })

  lifecycle { ignore_changes = [tags] }
}

# Blob storage containers will be deleted automatically after 60 days.
resource "azurerm_storage_management_policy" "sa_export_approved" {
  storage_account_id = azurerm_storage_account.sa_export_approved.id
  rule {
    name    = "auto_delete_after_given_period"
    enabled = true
    filters {
      blob_types = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_creation_greater_than = 60
      }
    }
  }
}

resource "azurerm_private_endpoint" "stg_export_approved_pe" {
  name                = "stg-app-export-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-export-app"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stgappexport-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_export_approved.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'In-Progress' storage account
resource "azurerm_storage_account" "sa_import_in_progress" {
  name                            = local.import_in_progress_storage_name
  location                        = var.location
  resource_group_name             = var.resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;in-progress"
  })

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [tags] }
}

# Enable Airlock Malware Scanning on Core TRE
resource "azapi_resource_action" "enable_defender_for_storage" {
  count       = var.enable_malware_scanning ? 1 : 0
  type        = "Microsoft.Security/defenderForStorageSettings@2022-12-01-preview"
  resource_id = "${azurerm_storage_account.sa_import_in_progress.id}/providers/Microsoft.Security/defenderForStorageSettings/current"
  method      = "PUT"

  body = jsonencode({
    properties = {
      isEnabled = true
      malwareScanning = {
        onUpload = {
          isEnabled     = true
          capGBPerMonth = 5000
        },
        scanResultsEventGridTopicResourceId = azurerm_eventgrid_topic.scan_result[0].id
      }
      sensitiveDataDiscovery = {
        isEnabled = true
      }
      overrideSubscriptionLevelSettings = true
    }
  })
}

resource "azurerm_private_endpoint" "stg_import_inprogress_pe" {
  name                = "stg-ip-import-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-import-ip"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stgipimport-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_in_progress.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}


# 'Rejected' storage account
resource "azurerm_storage_account" "sa_import_rejected" {
  name                            = local.import_rejected_storage_name
  location                        = var.location
  resource_group_name             = var.resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;rejected"
  })

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [tags] }
}

# Blob storage containers will be deleted automatically after 60 days.
resource "azurerm_storage_management_policy" "sa_import_rejected" {
  storage_account_id = azurerm_storage_account.sa_import_rejected.id
  rule {
    name    = "auto_delete_after_given_period"
    enabled = true
    filters {
      blob_types = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_creation_greater_than = 60
      }
    }
  }
}

resource "azurerm_private_endpoint" "stg_import_rejected_pe" {
  name                = "stg-import-rej-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-import-rej"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-import-rej-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_rejected.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }

  tags = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

# 'Blocked' storage account
resource "azurerm_storage_account" "sa_import_blocked" {
  name                            = local.import_blocked_storage_name
  location                        = var.location
  resource_group_name             = var.resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;blocked"
  })

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [tags] }
}

# Blob storage containers will be deleted automatically after 60 days.
resource "azurerm_storage_management_policy" "sa_import_blocked" {
  storage_account_id = azurerm_storage_account.sa_import_blocked.id
  rule {
    name    = "auto_delete_after_given_period"
    enabled = true
    filters {
      blob_types = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_creation_greater_than = 60
      }
    }
  }
}

resource "azurerm_private_endpoint" "stg_import_blocked_pe" {
  name                = "stg-import-blocked-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id

  private_dns_zone_group {
    name                 = "private-dns-zone-group-stg-import-blocked"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-import-rej-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_blocked.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }

  tags = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}
