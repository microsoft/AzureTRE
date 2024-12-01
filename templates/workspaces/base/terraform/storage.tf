resource "azurerm_storage_account" "stg" {
  name                             = local.storage_name
  resource_group_name              = azurerm_resource_group.ws.name
  location                         = azurerm_resource_group.ws.location
  account_tier                     = "Standard"
  account_replication_type         = "GRS"
  allow_nested_items_to_be_public  = false
  is_hns_enabled                   = true
  cross_tenant_replication_enabled = false // not technically needed as cross tenant replication not supported when is_hns_enabled = true
  tags                             = local.tre_workspace_tags

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.encryption_identity[0].id]
    }
  }

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

# Using AzAPI as AzureRM uses shared account key for Azure files operations
resource "azapi_resource" "shared_storage" {
  type      = "Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01"
  name      = "vm-shared-storage"
  parent_id = "${azurerm_storage_account.stg.id}/fileServices/default"
  body = jsonencode({
    properties = {
      shareQuota       = var.shared_storage_quota
      enabledProtocols = "SMB"
    }
  })

  depends_on = [
    azurerm_private_endpoint.stgfilepe,
    azurerm_storage_account_network_rules.stgrules
  ]
}

resource "azurerm_storage_container" "stgcontainer" {
  name                  = "datalake"
  storage_account_name  = azurerm_storage_account.stg.name
  container_access_type = "private"

  depends_on = [
    azurerm_private_endpoint.stgblobpe,
    azurerm_storage_account_network_rules.stgrules
  ]
}

resource "azurerm_storage_account_network_rules" "stgrules" {
  storage_account_id = azurerm_storage_account.stg.id

  # When deploying from a local machine we need to "allow"
  default_action = var.enable_local_debugging ? "Allow" : "Deny"
  bypass         = ["AzureServices"]
}

resource "azurerm_private_endpoint" "stgfilepe" {
  name                = "stgfilepe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.filecore_zone_id]
  }

  private_service_connection {
    name                           = "stgfilepesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["File"]
  }
}

resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "stgblobpe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network,
    azurerm_private_endpoint.stgfilepe
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.blobcore_zone_id]
  }

  private_service_connection {
    name                           = "stgblobpesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

resource "azurerm_private_endpoint" "stgdfspe" {
  name                = "stgdfspe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network,
    azurerm_private_endpoint.stgblobpe
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.dfscore_zone_id]
  }

  private_service_connection {
    name                           = "stgdfspesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }
}

resource "azurerm_storage_account_customer_managed_key" "stg_encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  storage_account_id        = azurerm_storage_account.stg.id
  key_vault_id              = var.key_store_id
  key_name                  = local.kv_encryption_key_name
  user_assigned_identity_id = azurerm_user_assigned_identity.encryption_identity[0].id

  depends_on = [ azurerm_key_vault_key.encryption_key ]
}
