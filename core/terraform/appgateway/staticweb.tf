# See https://microsoft.github.io/AzureTRE/tre-developers/letsencrypt/
resource "azurerm_storage_account" "staticweb" {
  name                            = local.staticweb_storage_name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  enable_https_traffic_only       = true
  allow_nested_items_to_be_public = false
  tags                            = local.tre_core_tags

  static_website {
    index_document     = "index.html"
    error_404_document = "index.html"
  }

  lifecycle { ignore_changes = [tags] }

  network_rules {
    bypass         = ["AzureServices"]
    default_action = "Deny"
  }

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }
}

resource "azurerm_storage_account_customer_managed_key" "staticweb_encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  storage_account_id        = azurerm_storage_account.staticweb.id
  key_vault_id              = var.key_store_id
  key_name                  = var.kv_encryption_key_name
  user_assigned_identity_id = var.encryption_identity_id

  lifecycle {
    ignore_changes = [
      key_vault_id
    ]
  }
}

# Assign the "Storage Blob Data Contributor" role needed for uploading certificates to the storage account
resource "azurerm_role_assignment" "stgwriter" {
  scope                = azurerm_storage_account.staticweb.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.deployer.object_id
}

resource "azurerm_private_endpoint" "webpe" {
  name                = "pe-web-${local.staticweb_storage_name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-web"
    private_dns_zone_ids = [var.static_web_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-web-${local.staticweb_storage_name}"
    private_connection_resource_id = azurerm_storage_account.staticweb.id
    is_manual_connection           = false
    subresource_names              = ["web"]
  }
}
