resource "azurerm_storage_account" "cyclecloud" {
  name                             = local.storage_name
  location                         = data.azurerm_resource_group.rg.location
  resource_group_name              = data.azurerm_resource_group.rg.name
  account_tier                     = "Standard"
  account_replication_type         = "GRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  cross_tenant_replication_enabled = false
  tags                             = local.tre_shared_service_tags

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [data.azurerm_user_assigned_identity.tre_encryption_identity[0].id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = data.azurerm_key_vault_key.encryption_key[0].versionless_id
      user_assigned_identity_id = data.azurerm_user_assigned_identity.tre_encryption_identity[0].id
    }
  }

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "pe-${local.storage_name}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  subnet_id           = data.azurerm_subnet.shared.id
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "pesc-${local.storage_name}"
    private_connection_resource_id = azurerm_storage_account.cyclecloud.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}
