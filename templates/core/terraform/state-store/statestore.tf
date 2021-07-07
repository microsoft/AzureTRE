resource "azurerm_cosmosdb_account" "tre-db-account" {
  name                = "cosmos-${var.tre_id}"
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

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_cosmosdb_sql_database" "tre-db" {
  name                = "AzureTRE"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.tre-db-account.name
  throughput          = 400
}

resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos_documents_dns_link" {
  name                  = "cosmos_documents_dns_link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos.name
  virtual_network_id    = var.core_vnet

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_endpoint" "sspe" {
  name                = "pe-ss-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet

  lifecycle { ignore_changes = [ tags ] }

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
