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
  location                          = data.azurerm_resource_group.rg.location
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
  ssl_enforcement_enabled           = true
  ssl_minimal_tls_version_enforced  = "TLS1_2"
  tags                              = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags, threat_detection_policy] }
}

resource "azurerm_mysql_database" "gitea" {
  name                = "gitea"
  resource_group_name = local.core_resource_group_name
  server_name         = azurerm_mysql_server.gitea.name
  charset             = "utf8"
  collation           = "utf8_unicode_ci"
}

moved {
  from = azurerm_private_endpoint.private-endpoint
  to   = azurerm_private_endpoint.private_endpoint
}

resource "azurerm_private_endpoint" "private_endpoint" {
  name                = "pe-${azurerm_mysql_server.gitea.name}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name
  subnet_id           = data.azurerm_subnet.shared.id
  tags                = local.tre_shared_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_mysql_server.gitea.id
    name                           = "psc-${azurerm_mysql_server.gitea.name}"
    subresource_names              = ["mysqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "privatelink.mysql.database.azure.com"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.mysql.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "${azurerm_mysql_server.gitea.name}-administrator-password"
  value        = random_password.password.result
  key_vault_id = data.azurerm_key_vault.keyvault.id
  tags         = local.tre_shared_service_tags

  depends_on = [
    azurerm_key_vault_access_policy.gitea_policy
  ]
}
