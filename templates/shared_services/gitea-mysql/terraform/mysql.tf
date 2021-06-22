resource "random_password" "password" {
  length      = 20
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
}
resource "azurerm_mysql_server" "gitea" {
  name                              = "mysql-${var.tre_id}"
  resource_group_name               = local.core_resource_group_name
  location                          = var.location
  administrator_login               = "mysqladmin"
  administrator_login_password      = random_password.password.result
  sku_name                          = "GP_Gen5_2"
  storage_mb                        = 5120
  version                           = "8.0"
  auto_grow_enabled                 = true
  backup_retention_days             = 7
  geo_redundant_backup_enabled      = false
  infrastructure_encryption_enabled = false
  public_network_access_enabled     = false

  # Bug 
  ssl_enforcement_enabled           = false
  ssl_minimal_tls_version_enforced  = "TLSEnforcementDisabled"
}

resource "azurerm_mysql_database" "gitea" {
  name                = "gitea"
  resource_group_name = local.core_resource_group_name
  server_name         = azurerm_mysql_server.gitea.name
  charset             = "utf8"
  collation           = "utf8_unicode_ci"
}

resource "azurerm_private_endpoint" "private-endpoint" {
  name                = "pe-mysql-${var.tre_id}"
  location            = var.location
  resource_group_name = local.core_resource_group_name
  subnet_id           = data.azurerm_subnet.shared.id

  private_service_connection {
    private_connection_resource_id = azurerm_mysql_server.gitea.id
    name                           = "pec-mysql-${var.tre_id}"
    subresource_names              = ["mysqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.mysql.database.azure.com"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.mysql.id]
  }
}
