resource "random_string" "username" {
  length    = 10
  upper     = true
  lower     = true
  numeric   = false
  min_lower = 1
  special   = false
}

resource "random_password" "password" {
  length           = 16
  lower            = true
  min_lower        = 1
  upper            = true
  min_upper        = 1
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%$"
}

resource "azurerm_key_vault_secret" "postgresql_admin_username" {
  name         = "${local.postgresql_server_name}-admin-username"
  value        = random_string.username.result
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "postgresql_admin_password" {
  name         = "${local.postgresql_server_name}-admin-password"
  value        = random_password.password.result
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_postgresql_server" "mlflow" {
  name                = local.postgresql_server_name
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_workspace_service_tags

  administrator_login          = random_string.username.result
  administrator_login_password = random_password.password.result

  sku_name   = "GP_Gen5_2"
  version    = "11"
  storage_mb = 5120

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  auto_grow_enabled            = true

  public_network_access_enabled    = false
  ssl_enforcement_enabled          = true
  ssl_minimal_tls_version_enforced = "TLS1_2"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_postgresql_database" "mlflow" {
  name                = "mlflowdb"
  resource_group_name = data.azurerm_resource_group.ws.name
  server_name         = azurerm_postgresql_server.mlflow.name
  charset             = "UTF8"
  collation           = "English_United States.1252"
}

resource "azurerm_private_endpoint" "private_endpoint" {
  name                = "pe-${azurerm_postgresql_server.mlflow.name}-postgres"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_postgresql_server.mlflow.id
    name                           = "psc-${azurerm_postgresql_server.mlflow.name}"
    subresource_names              = ["postgresqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.postgres.database.azure.com"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.postgres.id]
  }

  lifecycle { ignore_changes = [tags] }
}
