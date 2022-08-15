# 'Approved' storage account
resource "azurerm_storage_account" "sa_import_approved" {
  name                            = local.import_approved_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  tags = merge(
    var.tre_workspace_tags,
    {
      description = "airlock;import;approved"
    }
  )

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "import_approved_pe" {
  name                = "pe-sa-import-approved-blob-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-sa-import-approved"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-sa-import-approved-${var.short_workspace_id}"
    private_connection_resource_id = azurerm_storage_account.sa_import_approved.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}


# 'Drop' location for export
resource "azurerm_storage_account" "sa_export_internal" {
  name                            = local.export_internal_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  tags = merge(
    var.tre_workspace_tags,
    {
      description = "airlock;export;internal"
    }
  )

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_endpoint" "export_internal_pe" {
  name                = "pe-sa-export-int-blob-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-sa-export-int"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-sa-export-int-${var.short_workspace_id}"
    private_connection_resource_id = azurerm_storage_account.sa_export_internal.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'In-progress' location for export
resource "azurerm_storage_account" "sa_export_inprogress" {
  name                            = local.export_inprogress_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  tags = merge(
    var.tre_workspace_tags,
    {
      description = "airlock;export;inprogress"
    }
  )

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_account_network_rules" "sa_export_inprogress_rules" {
  storage_account_id = azurerm_storage_account.sa_export_inprogress.id

  # When the Airlock procssor tried to copy data from the export in-progress SA to the Export approved SA, its not using the PE, as the destination is public, hence, allowing this subnet is mandatory
  # It might be possible to add PE to this storage instead of opening the fw to this subnet: https://github.com/microsoft/AzureTRE/issues/2098
  virtual_network_subnet_ids = [var.airlock_processor_subnet_id]

  default_action = var.enable_local_debugging ? "Allow" : "Deny"
  bypass         = ["AzureServices"]
}


resource "azurerm_private_endpoint" "export_inprogress_pe" {
  name                = "pe-sa-ip-export-blob-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-sa-export-ip"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-sa-export-ip-${var.short_workspace_id}"
    private_connection_resource_id = azurerm_storage_account.sa_export_inprogress.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'Rejected' location for export
resource "azurerm_storage_account" "sa_export_rejected" {
  name                            = local.export_rejected_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  tags = merge(
    var.tre_workspace_tags,
    {
      description = "airlock;export;rejected"
    }
  )

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_endpoint" "export_rejected_pe" {
  name                = "pe-sa-export-rej-blob-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-sa-export-rej"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-sa-export-rej-${var.short_workspace_id}"
    private_connection_resource_id = azurerm_storage_account.sa_export_rejected.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# 'Blocked' location for export
resource "azurerm_storage_account" "sa_export_blocked" {
  name                            = local.export_blocked_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  # Important! we rely on the fact that the blob craeted events are issued when the creation of the blobs are done.
  # This is true ONLY when Hierarchical Namespace is DISABLED
  is_hns_enabled = false

  network_rules {
    default_action = var.enable_local_debugging ? "Allow" : "Deny"
    bypass         = ["AzureServices"]
  }

  tags = merge(
    var.tre_workspace_tags,
    {
      description = "airlock;export;blocked"
    }
  )

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_endpoint" "export_blocked_pe" {
  name                = "pe-sa-export-blocked-blob-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-sa-export-blocked"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-sa-export-blocked-${var.short_workspace_id}"
    private_connection_resource_id = azurerm_storage_account.sa_export_blocked.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# we can't use for_each due to the data object
resource "azurerm_role_assignment" "airlock_blob_data_contributor" {
  count                = length(local.airlock_blob_data_contributor)
  scope                = local.airlock_blob_data_contributor[count.index]
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
}

# This might be considered redundent since we give Virtual Machine Contributor
# at the subscription level, but best to be explicit.
resource "azurerm_role_assignment" "api_sa_data_contributor" {
  count                = length(local.api_sa_data_contributor)
  scope                = local.api_sa_data_contributor[count.index]
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
}
