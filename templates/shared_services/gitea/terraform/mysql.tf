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
  sku_name                     = "GP_Standard_D2ds_v4"
  version                      = "8.0.21"
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  delegated_subnet_id          = data.azurerm_subnet.mysql_gitea_shared_service.id
  private_dns_zone_id          = data.azurerm_private_dns_zone.mysql.id
  tags                         = local.tre_shared_service_tags

  storage {
    size_gb           = 20
    auto_grow_enabled = true
  }

  lifecycle {
    ignore_changes = [
      tags,
      zone
    ]
  }
}

resource "azurerm_mysql_flexible_database" "gitea" {
  name                = "gitea"
  resource_group_name = local.core_resource_group_name
  server_name         = azurerm_mysql_flexible_server.gitea.name
  charset             = "utf8"
  collation           = "utf8_unicode_ci"
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "${azurerm_mysql_flexible_server.gitea.name}-administrator-password"
  value        = random_password.password.result
  key_vault_id = data.azurerm_key_vault.keyvault.id
  tags         = local.tre_shared_service_tags

  depends_on = [
    azurerm_key_vault_access_policy.gitea_policy
  ]
}
