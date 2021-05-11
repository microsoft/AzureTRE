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

resource "azurerm_private_dns_zone" "statestore" {
  name                = "privatelink.statestore.azure.net"
  resource_group_name = var.resource_group_name
}

resource "azurerm_private_dns_zone_virtual_network_link" "statestorelink" {
  name                  = "statestorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.statestore.name
  virtual_network_id    = var.core_vnet
}

resource "azurerm_private_endpoint" "sspe" {
  name                = "pe-ss-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.statestore.id]
  }

  private_service_connection {
    name                           = "psc-ss-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
    private_connection_resource_id = azurerm_cosmosdb_account.tre-db-account.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }
}
