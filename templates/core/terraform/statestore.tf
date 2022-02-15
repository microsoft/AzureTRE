resource "azurerm_cosmosdb_account" "tre-db-account" {
  name                = "cosmos-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  enable_automatic_failover = false

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

resource "azurerm_cosmosdb_sql_database" "tre-db" {
  name                = "AzureTRE"
  resource_group_name = azurerm_resource_group.core.name
  account_name        = azurerm_cosmosdb_account.tre-db-account.name
  throughput          = 400
}

resource "azurerm_management_lock" "tre-db" {
  count      = var.debug == true ? 0 : 1
  name       = "tre-db-lock"
  scope      = azurerm_cosmosdb_sql_database.tre-db.id
  lock_level = "CanNotDelete"
  notes      = "Locked to prevent accidental deletion"
}

resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = azurerm_resource_group.core.name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos_documents_dns_link" {
  name                  = "cosmos_documents_dns_link"
  resource_group_name   = azurerm_resource_group.core.name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos.name
  virtual_network_id    = module.network.core_vnet_id

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "sspe" {
  name                = "pe-ss-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.shared_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos.id]
  }

  private_service_connection {
    name                           = "psc-ss-${var.tre_id}"
    private_connection_resource_id = azurerm_cosmosdb_account.tre-db-account.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }
}
