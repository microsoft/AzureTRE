resource "azurerm_cosmosdb_account" "tre_db_account" {
  name                          = "cosmos-${var.tre_id}"
  location                      = azurerm_resource_group.core.location
  resource_group_name           = azurerm_resource_group.core.name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  automatic_failover_enabled    = false
  public_network_access_enabled = var.enable_local_debugging
  ip_range_filter               = local.cosmos_ip_filter_set
  local_authentication_disabled = true
  tags                          = local.tre_core_tags

  dynamic "capabilities" {
    # We can't change an existing cosmos
    for_each = var.is_cosmos_defined_throughput ? [] : [1]
    content {
      name = "EnableServerless"
    }
  }

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.encryption[0].id]
    }
  }

  key_vault_key_id      = var.enable_cmk_encryption ? azurerm_key_vault_key.tre_encryption[0].versionless_id : null
  default_identity_type = var.enable_cmk_encryption ? "UserAssignedIdentity=${azurerm_user_assigned_identity.encryption[0].id}" : null

  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 10
    max_staleness_prefix    = 200
  }

  geo_location {
    location          = azurerm_resource_group.core.location
    failover_priority = 0
  }

  lifecycle { ignore_changes = [tags] }
}

moved {
  from = azurerm_cosmosdb_account.tre-db-account
  to   = azurerm_cosmosdb_account.tre_db_account
}

resource "azurerm_cosmosdb_sql_database" "tre_db" {
  name                = "AzureTRE"
  resource_group_name = azurerm_resource_group.core.name
  account_name        = azurerm_cosmosdb_account.tre_db_account.name
}

moved {
  from = azurerm_cosmosdb_sql_database.tre-db
  to   = azurerm_cosmosdb_sql_database.tre_db
}

resource "azurerm_management_lock" "tre_db" {
  count      = var.stateful_resources_locked ? 1 : 0
  name       = "tre-db-lock"
  scope      = azurerm_cosmosdb_sql_database.tre_db.id
  lock_level = "CanNotDelete"
  notes      = "Locked to prevent accidental deletion"
}

moved {
  from = azurerm_management_lock.tre-db
  to   = azurerm_management_lock.tre_db
}

resource "azurerm_private_dns_zone" "cosmos" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.documents.azure.com"]
  resource_group_name = azurerm_resource_group.core.name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos_documents_dns_link" {
  name                  = "cosmos_documents_dns_link"
  resource_group_name   = azurerm_resource_group.core.name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos.name
  virtual_network_id    = module.network.core_vnet_id
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "sspe" {
  name                = "pe-ss-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.shared_subnet_id
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos.id]
  }

  private_service_connection {
    name                           = "psc-ss-${var.tre_id}"
    private_connection_resource_id = azurerm_cosmosdb_account.tre_db_account.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }
}
