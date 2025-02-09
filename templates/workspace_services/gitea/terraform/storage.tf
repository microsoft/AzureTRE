resource "azurerm_storage_account" "gitea" {
  name                             = local.storage_name
  resource_group_name              = data.azurerm_resource_group.ws.name
  location                         = data.azurerm_resource_group.ws.location
  account_tier                     = "Standard"
  account_replication_type         = "GRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  cross_tenant_replication_enabled = false
  tags                             = local.workspace_service_tags

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [data.azurerm_user_assigned_identity.ws_encryption_identity[0].id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = data.azurerm_key_vault_key.ws_encryption_key[0].versionless_id
      user_assigned_identity_id = data.azurerm_user_assigned_identity.ws_encryption_identity[0].id
    }
  }

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_storage_account_network_rules" "stgrules" {
  storage_account_id = azurerm_storage_account.gitea.id

  default_action = "Deny"
  bypass         = ["AzureServices"]
}

resource "azurerm_private_endpoint" "stgfilepe" {
  name                = "stgfilepe-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.filecore.id]
  }

  private_service_connection {
    name                           = "stgfilepesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.gitea.id
    is_manual_connection           = false
    subresource_names              = ["File"]
  }
}


resource "azurerm_storage_share" "gitea" {
  name                 = "gitea-data"
  storage_account_name = azurerm_storage_account.gitea.name
  quota                = var.gitea_storage_limit
}
