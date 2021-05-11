resource "azurerm_cosmosdb_account" "tre-db-account" {
  name                = "cosmos-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  enable_automatic_failover = false
 
  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 10
    max_staleness_prefix    = 200
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "tre-db" {
  name                = "cosmos-sql-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.tre-db-account.name
  throughput          = 400
}
