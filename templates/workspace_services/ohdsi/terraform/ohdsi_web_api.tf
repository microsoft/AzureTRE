resource "azurerm_key_vault_secret" "jdbc_connection_string_webapi_admin" {
  name         = "jdbc-connectionstring-${local.short_service_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
  value        = "jdbc:postgresql://${azurerm_postgresql_flexible_server.postgres.fqdn}:5432/${local.postgres_webapi_database_name}?user=${local.postgres_webapi_admin_username}&password=${azurerm_key_vault_secret.postgres_webapi_admin_password.value}&sslmode=require"
  tags         = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_user_assigned_identity" "ohdsi_webapi_id" {
  name                = "id-ohdsi-webapi-${local.service_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "keyvault_ohdsi_ws_role" {
  scope                = data.azurerm_key_vault.ws.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.ohdsi_webapi_id.principal_id
}

resource "azurerm_linux_web_app" "ohdsi_webapi" {
  name                      = local.ohdsi_webapi_name
  location                  = data.azurerm_resource_group.ws.location
  resource_group_name       = data.azurerm_resource_group.ws.name
  virtual_network_subnet_id = data.azurerm_subnet.web_app.id

  service_plan_id         = data.azurerm_service_plan.workspace.id
  https_only              = true
  client_affinity_enabled = false

  site_config {
    always_on           = true
    ftps_state          = "Disabled"
    minimum_tls_version = "1.3"

    application_stack {
      docker_image_name = "index.docker.io/${local.ohdsi_api_docker_image_name}:${local.ohdsi_api_docker_image_tag}"
    }
  }

  key_vault_reference_identity_id = azurerm_user_assigned_identity.ohdsi_webapi_id.id

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.ohdsi_webapi_id.id]
  }

  app_settings = {
    "DATASOURCE_DRIVERCLASSNAME"                     = "org.postgresql.Driver"
    "DATASOURCE_OHDSI_SCHEMA"                        = local.postgres_schema_name
    "DATASOURCE_USERNAME"                            = local.postgres_webapi_app_username
    "DATASOURCE_PASSWORD"                            = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${azurerm_key_vault_secret.postgres_webapi_app_password.name})"
    "DATASOURCE_URL"                                 = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${azurerm_key_vault_secret.jdbc_connection_string_webapi_admin.name})"
    "FLYWAY_BASELINEDESCRIPTION"                     = "Base Migration"
    "FLYWAY_BASELINEONMIGRATE"                       = "true"
    "flyway_baselineVersionAsString"                 = local.ohdsi_api_flyway_baseline_version
    "FLYWAY_DATASOURCE_DRIVERCLASSNAME"              = "org.postgresql.Driver"
    "FLYWAY_DATASOURCE_USERNAME"                     = local.postgres_webapi_admin_username
    "FLYWAY_DATASOURCE_PASSWORD"                     = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${azurerm_key_vault_secret.postgres_webapi_admin_password.name})"
    "FLYWAY_DATASOURCE_URL"                          = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${azurerm_key_vault_secret.jdbc_connection_string_webapi_admin.name})"
    "FLYWAY_LOCATIONS"                               = "classpath:db/migration/postgresql"
    "FLYWAY_PLACEHOLDERS_OHDSISCHEMA"                = local.postgres_schema_name
    "FLYWAY_SCHEMAS"                                 = local.postgres_schema_name
    "FLYWAY_TABLE"                                   = "schema_history"
    "MANAGED_IDENTITY_CLIENT_ID"                     = azurerm_user_assigned_identity.ohdsi_webapi_id.id
    "SECURITY_SSL_ENABLED"                           = "false"
    "SECURITY_CORS_ENABLED"                          = "true"
    "SECURITY_DB_DATASOURCE_AUTHENTICATIONQUERY"     = "select password from webapi_security.security where email = ?"
    "SECURITY_DB_DATASOURCE_PASSWORD"                = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${azurerm_key_vault_secret.postgres_webapi_admin_password.name})"
    "SECURITY_DB_DATASOURCE_SCHEMA"                  = "webapi_security"
    "SECURITY_DB_DATASOURCE_URL"                     = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${azurerm_key_vault_secret.jdbc_connection_string_webapi_admin.name})"
    "SECURITY_DB_DATASOURCE_USERNAME"                = local.postgres_webapi_admin_username
    "SECURITY_DURATION_INCREMENT"                    = "10"
    "SECURITY_DURATION_INITIAL"                      = "10"
    "SECURITY_MAXLOGINATTEMPTS"                      = "3"
    "SECURITY_ORIGIN"                                = "*"
    "SECURITY_PROVIDER"                              = "AtlasRegularSecurity"
    "SPRING_BATCH_REPOSITORY_TABLEPREFIX"            = "webapi.BATCH_"
    "SPRING_JPA_PROPERTIES_HIBERNATE_DEFAULT_SCHEMA" = local.postgres_schema_name
    "SPRING_JPA_PROPERTIES_HIBERNATE_DIALECT"        = "org.hibernate.dialect.PostgreSQLDialect"
    "WEBSITES_CONTAINER_START_TIME_LIMIT"            = "1800"
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE"            = false
    "WEBSITES_PORT"                                  = "8080"
    "security.oid.clientId"                          = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${data.azurerm_key_vault_secret.workspace_client_id.name})"
    "security.oid.apiSecret"                         = "@Microsoft.KeyVault(VaultName=${data.azurerm_key_vault.ws.name};SecretName=${data.azurerm_key_vault_secret.workspace_client_secret.name})"
    "security.oid.url"                               = "${module.terraform_azurerm_environment_configuration.active_directory_endpoint}/${data.azurerm_key_vault_secret.aad_tenant_id.value}/v2.0/.well-known/openid-configuration"
    "security.oauth.callback.api"                    = local.ohdsi_webapi_url_auth_callback
    "security.oauth.callback.ui"                     = local.atlas_ui_url_welcome
    "security.oid.redirectUrl"                       = local.atlas_ui_url_welcome
    "security.oid.logoutUrl"                         = local.atlas_ui_url_welcome
  }

  logs {
    application_logs {
      file_system_level = "Information"
    }

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 100
      }
    }
  }

  tags = local.tre_workspace_service_tags

  depends_on = [
    terraform_data.deployment_ohdsi_webapi_init
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "webapi_private_endpoint" {
  name                = "pe-${azurerm_linux_web_app.ohdsi_webapi.name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_linux_web_app.ohdsi_webapi.id
    name                           = "psc-${azurerm_linux_web_app.ohdsi_webapi.name}"
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.azurewebsites.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_diagnostic_setting" "ohdsi_webapi" {
  name                       = azurerm_linux_web_app.ohdsi_webapi.name
  target_resource_id         = azurerm_linux_web_app.ohdsi_webapi.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.workspace.id

  dynamic "enabled_log" {
    for_each = local.ohdsi_api_log_analytics_categories
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
