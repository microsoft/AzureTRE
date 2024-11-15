resource "random_password" "password" {
  length      = 20
  min_upper   = 2
  min_lower   = 2
  min_numeric = 2
  min_special = 2
}

resource "azurerm_mysql_flexible_server" "gitea" {
  name                         = "mysql-${var.tre_id}"
  resource_group_name          = local.core_resource_group_name
  location                     = data.azurerm_resource_group.rg.location
  administrator_login          = "mysqladmin"
  administrator_password       = random_password.password.result
  sku_name                     = local.sql_sku[var.sql_sku].value
  version                      = "8.0.21"
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  tags                         = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags, zone] }
}

resource "azurerm_mysql_flexible_database" "gitea" {
  name                = "gitea"
  resource_group_name = local.core_resource_group_name
  server_name         = azurerm_mysql_flexible_server.gitea.name
  charset             = "utf8"
  collation           = "utf8_unicode_ci"

  lifecycle { ignore_changes = [charset, collation] }
}

moved {
  from = azurerm_private_endpoint.private-endpoint
  to   = azurerm_private_endpoint.private_endpoint
}

resource "azurerm_private_endpoint" "private_endpoint" {
  name                = "pe-${azurerm_mysql_flexible_server.gitea.name}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name
  subnet_id           = data.azurerm_subnet.shared.id
  tags                = local.tre_shared_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_mysql_flexible_server.gitea.id
    name                           = "psc-${azurerm_mysql_flexible_server.gitea.name}"
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
  name         = "${azurerm_mysql_flexible_server.gitea.name}-administrator-password"
  value        = random_password.password.result
  key_vault_id = data.azurerm_key_vault.keyvault.id
  tags         = local.tre_shared_service_tags

  depends_on = [
    azurerm_role_assignment.keyvault_gitea_role
  ]

  lifecycle { ignore_changes = [tags] }
}
