resource "azurerm_storage_account" "stg" {
  name                            = lower(replace("stg-${var.tre_id}", "-", ""))
  resource_group_name             = azurerm_resource_group.core.name
  location                        = azurerm_resource_group.core.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  tags                            = local.tre_core_tags
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
}

resource "azurerm_private_endpoint" "tablepe" {
  name                = "pe-table-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.shared_subnet_id
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-tablecore"
    private_dns_zone_ids = [module.network.table_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-tablestg-${var.tre_id}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Table"]
  }
}

resource "azurerm_storage_table" "workspacecosts" {
  name                 = "workspacecosts"
  storage_account_name = azurerm_storage_account.stg.name
}

resource "azurerm_storage_table" "workspacecreditusage" {
  name                 = "workspacecreditusage"
  storage_account_name = azurerm_storage_account.stg.name
}


resource "azurerm_role_assignment" "workspace_costs_table_reader" {
  scope                = azurerm_storage_account.stg.id
  role_definition_name = "Storage Table Data Reader"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_storage_table" "storageusage" {
  name                 = "storageusage"
  storage_account_name = azurerm_storage_account.stg.name
}

resource "azurerm_role_assignment" "storageusage" {
  scope                = "${local.storage_table_scope}/${azurerm_storage_table.storageusage.name}"
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_storage_table" "fileshareusage" {
  name                 = "fileshareusage"
  storage_account_name = azurerm_storage_account.stg.name
}

resource "azurerm_role_assignment" "fileshareusage" {
  # scope                = azurerm_storage_table.fileshareusage.id
  scope                = "${local.storage_table_scope}/${azurerm_storage_table.fileshareusage.name}"
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}

resource "azurerm_storage_table" "perstudyusage" {
  name                 = "perstudyusage"
  storage_account_name = azurerm_storage_account.stg.name
}

resource "azurerm_role_assignment" "perstudtusage" {
  # scope                = azurerm_storage_table.perstudyusage.id
  scope                = "${local.storage_table_scope}/${azurerm_storage_table.perstudyusage.name}"
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}
