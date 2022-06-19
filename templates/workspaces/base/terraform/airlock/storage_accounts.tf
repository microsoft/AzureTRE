# 'Approved' storage account
resource "azurerm_storage_account" "sa_import_approved" {
  name                            = local.import_approved_storage_name
  location                        = var.location
  resource_group_name             = var.ws_resource_group_name
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
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
  account_replication_type        = "GRS"
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
  account_replication_type        = "GRS"
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
      description = "airlock;export;inprogress"
    }
  )

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_private_endpoint" "export_inprogress_pe" {
  name                = "pe-sa-ip-export-blob-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id

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
  account_replication_type        = "GRS"
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

resource "azurerm_role_assignment" "sa_import_approved" {
  scope                = azurerm_storage_account.sa_import_approved.id
  role_definition_name = "Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
}


resource "azurerm_role_assignment" "sa_export_internal" {
  scope                = azurerm_storage_account.sa_export_internal.id
  role_definition_name = "Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "sa_export_inprogress" {
  scope                = azurerm_storage_account.sa_export_inprogress.id
  role_definition_name = "Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
}

resource "azurerm_role_assignment" "sa_export_rejected" {
  scope                = azurerm_storage_account.sa_export_rejected.id
  role_definition_name = "Contributor"
  principal_id         = data.azurerm_user_assigned_identity.airlock_id.principal_id
}
