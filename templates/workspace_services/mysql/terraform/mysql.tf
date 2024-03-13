resource "random_password" "password" {
  length      = 20
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
}

resource "azurerm_mysql_flexible_server" "mysql" {
  name                              = "mysql-${local.service_resource_name_suffix}"
  resource_group_name               = data.azurerm_resource_group.ws.name
  location                          = data.azurerm_resource_group.ws.location
  administrator_login               = "mysqladmin"
  administrator_login_password      = random_password.password.result
  sku_name                          = local.sql_sku[var.sql_sku].value
  storage_mb                        = var.storage_mb
  version                           = "8.0"
  auto_grow_enabled                 = true
  backup_retention_days             = 7
  geo_redundant_backup_enabled      = false
  infrastructure_encryption_enabled = false
  public_network_access_enabled     = false
  ssl_enforcement_enabled           = true
  ssl_minimal_tls_version_enforced  = "TLS1_2"
  tags                              = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_mysql_database" "db" {
  name                = var.db_name
  resource_group_name = data.azurerm_resource_group.ws.name
  server_name         = azurerm_mysql_flexible_server.mysql.name
  charset             = "utf8"
  collation           = "utf8_unicode_ci"
}

resource "azurerm_private_endpoint" "mysql_private_endpoint" {
  name                = "pe-${azurerm_mysql_flexible_server.mysql.name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_mysql_flexible_server.mysql.id
    name                           = "psc-${azurerm_mysql_flexible_server.mysql.name}"
    subresource_names              = ["mysqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.mysql.database.azure.com"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.mysql.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "${azurerm_mysql_flexible_server.mysql.name}-administrator-password"
  value        = random_password.password.result
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}
