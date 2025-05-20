# See https://microsoft.github.io/AzureTRE/tre-developers/letsencrypt/
resource "azurerm_storage_account" "staticweb" {
  name                             = local.staticweb_storage_name
  resource_group_name              = var.resource_group_name
  location                         = var.location
  account_kind                     = "StorageV2"
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  https_traffic_only_enabled       = true
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = false
  local_user_enabled               = false
  tags                             = local.tre_core_tags

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }

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

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }
}

resource "azurerm_storage_account_static_website" "staticweb_site" {
  storage_account_id = azurerm_storage_account.staticweb.id
  index_document     = "index.html"
  error_404_document = "index.html"
}

# Assign the "Storage Blob Data Contributor" role needed for uploading certificates to the storage account
resource "azurerm_role_assignment" "stgwriter" {
  scope                = azurerm_storage_account.staticweb.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.deployer_principal_id
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
