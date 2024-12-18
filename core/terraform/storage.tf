resource "azurerm_storage_account" "stg" {
  name                             = lower(replace("stg-${var.tre_id}", "-", ""))
  resource_group_name              = azurerm_resource_group.core.name
  location                         = azurerm_resource_group.core.location
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.encryption[0].id]
    }
  }

  tags = local.tre_core_tags

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
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

resource "azurerm_storage_account_customer_managed_key" "encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  storage_account_id        = azurerm_storage_account.stg.id
  key_vault_id              = local.key_store_id
  key_name                  = local.cmk_name
  user_assigned_identity_id = azurerm_user_assigned_identity.encryption[0].id

  depends_on = [
    azurerm_role_assignment.kv_encryption_key_user[0],
    azurerm_key_vault_key.tre_encryption[0]
  ]
}
