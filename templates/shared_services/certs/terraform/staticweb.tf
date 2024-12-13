# See https://microsoft.github.io/AzureTRE/tre-developers/letsencrypt/
resource "azurerm_storage_account" "staticweb" {
  name                             = local.staticweb_storage_name
  resource_group_name              = data.azurerm_resource_group.rg.name
  location                         = data.azurerm_resource_group.rg.location
  account_kind                     = "StorageV2"
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  enable_https_traffic_only        = true
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  tags                             = local.tre_shared_service_tags

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  static_website {
    index_document     = "index.html"
    error_404_document = "404.html"
  }

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [data.azurerm_user_assigned_identity.tre_encryption_identity[0].id]
    }
  }

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_storage_account_customer_managed_key" "staticweb_stg_encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  storage_account_id        = azurerm_storage_account.staticweb.id
  key_vault_id              = var.key_store_id
  key_name                  = local.cmk_name
  user_assigned_identity_id = data.azurerm_user_assigned_identity.tre_encryption_identity[0].id

  depends_on = [azurerm_key_vault_key.encryption_key]
}

resource "azurerm_role_assignment" "stgwriter" {
  scope                = azurerm_storage_account.staticweb.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.resource_processor_vmss_id.principal_id
}
