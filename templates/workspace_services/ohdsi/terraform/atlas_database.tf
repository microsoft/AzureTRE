resource "random_password" "postgres_admin_password" {
  length  = 32
  special = false
}

resource "random_password" "postgres_webapi_admin_password" {
  length  = 32
  special = false
}

resource "random_password" "postgres_webapi_app_password" {
  length  = 32
  special = false
}

resource "azurerm_key_vault_secret" "postgres_admin_password" {
  name         = "postgres-admin-password-${local.short_service_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
  value        = random_password.postgres_admin_password.result
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "postgres_webapi_admin_password" {
  name         = "ohdsi-admin-password-${local.short_service_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
  value        = random_password.postgres_webapi_admin_password.result
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "postgres_webapi_app_password" {
  name         = "ohdsi-app-password-${local.short_service_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
  value        = random_password.postgres_webapi_app_password.result
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_network_security_group" "postgres" {
  name                = "nsg-psql-${local.service_suffix}"
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location

  tags = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  security_rule {
    name                         = "AllowWebAppsToPostgres"
    priority                     = 100
    direction                    = "Inbound"
    access                       = "Allow"
    protocol                     = "Tcp"
    source_port_range            = "*"
    destination_port_range       = "5432"
    source_address_prefixes      = [data.azurerm_subnet.web_app.address_prefix]
    destination_address_prefixes = azurerm_subnet.postgres.address_prefixes
  }

  security_rule {
    name                         = "AllowResourceProcessorToPostgres"
    priority                     = 101
    direction                    = "Inbound"
    access                       = "Allow"
    protocol                     = "Tcp"
    source_port_range            = "*"
    destination_port_range       = "5432"
    source_address_prefixes      = [data.azurerm_subnet.resource_processor.address_prefix]
    destination_address_prefixes = azurerm_subnet.postgres.address_prefixes
  }

  security_rule {
    name                       = "DenyInboundOverride"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "DenyOutboundOverride"
    priority                   = 4096
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

}

resource "azurerm_subnet" "postgres" {
  name                 = "PostgreSQLSubnet${local.short_service_id}"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
  address_prefixes     = [var.address_space]

  delegation {
    name = "psql-delegation"

    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet_network_security_group_association" "postgres" {
  subnet_id                 = azurerm_subnet.postgres.id
  network_security_group_id = azurerm_network_security_group.postgres.id
}

resource "terraform_data" "postgres_core_dns_link" {
  provisioner "local-exec" {

    environment = {
      RESOURCE_GROUP = local.core_resource_group_name
      DNS_ZONE_NAME  = data.azurerm_private_dns_zone.postgres.name
      VNET           = data.azurerm_virtual_network.core.name
    }

    command = "../scripts/postgres_dns_link.sh"
  }
}

resource "terraform_data" "postgres_subnet_wait" {
  provisioner "local-exec" {
    command = "sleep 30"
  }

  depends_on = [
    azurerm_subnet.postgres,
    azurerm_subnet_network_security_group_association.postgres,
    terraform_data.postgres_core_dns_link
  ]
}

resource "azurerm_postgresql_flexible_server" "postgres" {
  name                   = "psql-server-${local.service_suffix}"
  resource_group_name    = data.azurerm_resource_group.ws.name
  location               = data.azurerm_resource_group.ws.location
  delegated_subnet_id    = azurerm_subnet.postgres.id
  private_dns_zone_id    = data.azurerm_private_dns_zone.postgres.id
  sku_name               = var.postgres_sku
  version                = local.postgres_version
  administrator_login    = local.postgres_admin_username
  administrator_password = azurerm_key_vault_secret.postgres_admin_password.value
  storage_mb             = var.postgres_storage_size_in_mb
  zone                   = "1"
  tags                   = local.tre_workspace_service_tags

  timeouts {
    # If this doesn't complete in a realistic time, no point in waiting the full/default 60m
    create = "15m"
  }

  depends_on = [
    terraform_data.postgres_subnet_wait,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_postgresql_flexible_server_database" "db" {
  name      = local.postgres_webapi_database_name
  server_id = azurerm_postgresql_flexible_server.postgres.id
  charset   = "utf8"
  collation = "en_US.utf8"
}

resource "azurerm_monitor_diagnostic_setting" "postgres" {
  name                       = azurerm_postgresql_flexible_server.postgres.name
  target_resource_id         = azurerm_postgresql_flexible_server.postgres.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.workspace.id

  dynamic "enabled_log" {
    for_each = local.postgres_server_log_analytics_categories
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

resource "terraform_data" "deployment_ohdsi_webapi_init" {
  triggers_replace = {
    postgres_database_id = azurerm_postgresql_flexible_server_database.db.id
  }

  provisioner "local-exec" {

    environment = {
      MAIN_CONNECTION_STRING        = "host=${azurerm_postgresql_flexible_server.postgres.fqdn} port=5432 dbname=${local.postgres_webapi_database_name} user=${local.postgres_admin_username} password=${azurerm_key_vault_secret.postgres_admin_password.value} sslmode=require"
      OHDSI_ADMIN_CONNECTION_STRING = "host=${azurerm_postgresql_flexible_server.postgres.fqdn} port=5432 dbname=${local.postgres_webapi_database_name} user=${local.postgres_webapi_admin_username} password=${azurerm_key_vault_secret.postgres_webapi_admin_password.value} sslmode=require"
      DATABASE_NAME                 = local.postgres_webapi_database_name
      SCHEMA_NAME                   = local.postgres_schema_name
      OHDSI_ADMIN_PASSWORD          = azurerm_key_vault_secret.postgres_webapi_admin_password.value
      OHDSI_APP_PASSWORD            = azurerm_key_vault_secret.postgres_webapi_app_password.value
      OHDSI_APP_USERNAME            = local.postgres_webapi_app_username
      OHDSI_ADMIN_USERNAME          = local.postgres_webapi_admin_username
      OHDSI_ADMIN_ROLE              = local.postgres_webapi_admin_role
      OHDSI_APP_ROLE                = local.postgres_webapi_app_role
    }

    command = "sleep 60 && ../scripts/atlas_db_init.sh"
  }

  depends_on = [
    terraform_data.postgres_core_dns_link,
    azurerm_subnet_network_security_group_association.postgres
  ]
}
