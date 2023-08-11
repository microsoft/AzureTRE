resource "random_password" "atlas_security_admin_password" {
  length  = 8
  special = false
}

resource "azurerm_key_vault_secret" "atlas_security_admin_password" {
  name         = "atlas-security-admin-password-${local.short_service_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
  value        = random_password.atlas_security_admin_password.result
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "terraform_data" "deployment_atlas_security" {
  triggers_replace = {
    postgres_database_id = azurerm_postgresql_flexible_server_database.db.id
  }

  provisioner "local-exec" {
    environment = {
      OHDSI_ADMIN_CONNECTION_STRING = "host=${azurerm_postgresql_flexible_server.postgres.fqdn} port=5432 dbname=${local.postgres_webapi_database_name} user=${local.postgres_webapi_admin_username} password=${azurerm_key_vault_secret.postgres_webapi_admin_password.value} sslmode=require"
      ATLAS_SECURITY_ADMIN_PASSWORD = azurerm_key_vault_secret.atlas_security_admin_password.value
      ATLAS_USERS                   = "admin,${azurerm_key_vault_secret.atlas_security_admin_password.value}"
      WEB_API_URL                   = local.ohdsi_webapi_url
    }

    command = "../scripts/atlas_security.sh"
  }

  depends_on = [
    azurerm_postgresql_flexible_server_database.db,
    terraform_data.deployment_ohdsi_webapi_init,
    terraform_data.postgres_core_dns_link,
    azurerm_private_endpoint.webapi_private_endpoint,
    azurerm_subnet_network_security_group_association.postgres
  ]
}
