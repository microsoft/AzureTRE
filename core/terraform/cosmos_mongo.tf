resource "azurerm_cosmosdb_account" "mongo" {
  name                          = "cosmos-mongo-${var.tre_id}"
  location                      = azurerm_resource_group.core.location
  resource_group_name           = azurerm_resource_group.core.name
  offer_type                    = "Standard"
  kind                          = "MongoDB"
  automatic_failover_enabled    = false
  mongo_server_version          = 4.2
  ip_range_filter               = local.cosmos_ip_filter_set
  public_network_access_enabled = var.enable_local_debugging

  capabilities {
    name = "EnableServerless"
  }

  capabilities {
    name = "EnableMongo"
  }

  capabilities {
    name = "DisableRateLimitingResponses"
  }

  capabilities {
    name = "mongoEnableDocLevelTTL"
  }

  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = var.location
    failover_priority = 0
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

  tags = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_cosmosdb_mongo_database" "mongo" {
  name                = "porter"
  resource_group_name = azurerm_resource_group.core.name
  account_name        = azurerm_cosmosdb_account.mongo.name
}

resource "azurerm_management_lock" "mongo" {
  count      = var.stateful_resources_locked ? 1 : 0
  name       = "mongo-lock"
  scope      = azurerm_cosmosdb_mongo_database.mongo.id
  lock_level = "CanNotDelete"
  notes      = "Locked to prevent accidental deletion"
}

resource "azurerm_private_dns_zone" "mongo" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.mongo.cosmos.azure.com"]
  resource_group_name = azurerm_resource_group.core.name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "mongo" {
  name                  = "cosmos_mongo_dns_link"
  resource_group_name   = azurerm_resource_group.core.name
  private_dns_zone_name = azurerm_private_dns_zone.mongo.name
  virtual_network_id    = module.network.core_vnet_id
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "mongo" {
  name                = "pe-${azurerm_cosmosdb_account.mongo.name}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.resource_processor_subnet_id
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.mongo.id]
  }

  private_service_connection {
    name                           = "psc-${azurerm_cosmosdb_account.mongo.name}"
    private_connection_resource_id = azurerm_cosmosdb_account.mongo.id
    is_manual_connection           = false
    subresource_names              = ["MongoDB"]
  }
}

resource "azurerm_key_vault_secret" "cosmos_mongo_connstr" {
  name         = "porter-db-connection-string"
  value        = azurerm_cosmosdb_account.mongo.primary_mongodb_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  tags         = local.tre_core_tags
  depends_on = [
    azurerm_role_assignment.keyvault_deployer_role
  ]

  lifecycle { ignore_changes = [tags] }
}
