# Legacy (v1) per-stage storage accounts for airlock
# These are only deployed when enable_legacy_airlock = true
# Required for workspaces using airlock_version = 1

# 'External' storage account - drop location for import
resource "azurerm_storage_account" "sa_import_external" {
  count                            = var.enable_legacy_airlock ? 1 : 0
  name                             = local.import_external_storage_name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false
  allow_nested_items_to_be_public  = false

  is_hns_enabled                    = false
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;external"
  })

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_private_endpoint" "stg_import_external_pe" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = "pe-stg-import-external-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "pdzg-stg-import-external-blob-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-import-external-blob-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_external[0].id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'Approved' export
resource "azurerm_storage_account" "sa_export_approved" {
  count                            = var.enable_legacy_airlock ? 1 : 0
  name                             = local.export_approved_storage_name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false
  allow_nested_items_to_be_public  = false

  is_hns_enabled                    = false
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }

  tags = merge(var.tre_core_tags, {
    description = "airlock;export;approved"
  })

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_private_endpoint" "stg_export_approved_pe" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = "pe-stg-export-approved-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "pdzg-stg-export-approved-blob-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-export-approved-blob-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_export_approved[0].id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'In-Progress' storage account
resource "azurerm_storage_account" "sa_import_in_progress" {
  count                            = var.enable_legacy_airlock ? 1 : 0
  name                             = local.import_in_progress_storage_name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false

  is_hns_enabled                    = false
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;in-progress"
  })

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

# Enable Airlock Malware Scanning on legacy in-progress storage
resource "azapi_resource_action" "enable_defender_for_storage" {
  count       = var.enable_legacy_airlock && var.enable_malware_scanning ? 1 : 0
  type        = "Microsoft.Security/defenderForStorageSettings@2022-12-01-preview"
  resource_id = "${azurerm_storage_account.sa_import_in_progress[0].id}/providers/Microsoft.Security/defenderForStorageSettings/current"
  method      = "PUT"

  body = {
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
        isEnabled = false
      }
      overrideSubscriptionLevelSettings = true
    }
  }
}

resource "azurerm_private_endpoint" "stg_import_inprogress_pe" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = "pe-stg-import-inprogress-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "pdzg-stg-import-inprogress-blob-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-import-inprogress-blob-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_in_progress[0].id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'Rejected' storage account
resource "azurerm_storage_account" "sa_import_rejected" {
  count                            = var.enable_legacy_airlock ? 1 : 0
  name                             = local.import_rejected_storage_name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false

  is_hns_enabled                    = false
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;rejected"
  })

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_private_endpoint" "stg_import_rejected_pe" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = "pe-stg-import-rejected-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id

  private_dns_zone_group {
    name                 = "pdzg-stg-import-rejected-blob-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-import-rejected-blob-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_rejected[0].id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }

  tags = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

# 'Blocked' storage account
resource "azurerm_storage_account" "sa_import_blocked" {
  count                            = var.enable_legacy_airlock ? 1 : 0
  name                             = local.import_blocked_storage_name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false

  is_hns_enabled                    = false
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }

  tags = merge(var.tre_core_tags, {
    description = "airlock;import;blocked"
  })

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_private_endpoint" "stg_import_blocked_pe" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = "pe-stg-import-blocked-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_storage_subnet_id

  private_dns_zone_group {
    name                 = "pdzg-stg-import-blocked-blob-${var.tre_id}"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-stg-import-blocked-blob-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_blocked[0].id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }

  tags = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

# Legacy role assignments for v1 per-stage storage accounts
resource "azurerm_role_assignment" "airlock_blob_data_contributor" {
  count                = var.enable_legacy_airlock ? length(local.airlock_sa_blob_data_contributor) : 0
  scope                = local.airlock_sa_blob_data_contributor[count.index]
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "api_sa_data_contributor" {
  count                = var.enable_legacy_airlock ? length(local.api_sa_data_contributor) : 0
  scope                = local.api_sa_data_contributor[count.index]
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.api_principal_id
}
