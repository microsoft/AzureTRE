resource "terraform_data" "add_data_source" {

  count = var.configure_data_source ? 1 : 0

  triggers_replace = {
    postgres_database_id = azurerm_postgresql_flexible_server_database.db.id
  }

  provisioner "local-exec" {

    environment = {
      OHDSI_WEB_API_URL      = local.ohdsi_webapi_fqdn
      OHDSI_WEB_API_USER     = "admin"
      OHDSI_WEB_API_PASSWORD = azurerm_key_vault_secret.atlas_security_admin_password.value
      DIALECT                = local.dialects[local.data_source_config.dialect]
      SOURCE_NAME            = local.data_source_config.source_name
      SOURCE_KEY             = local.data_source_config.source_key
      CONNECTION_STRING      = local.data_source_config.connection_string
      USERNAME               = local.data_source_config.username
      PASSWORD               = local.data_source_config.password
      DAIMON_CDM             = try(local.data_source_daimons.daimon_cdm, null)
      DAIMON_VOCABULARY      = try(local.data_source_daimons.daimon_vocabulary, null)
      DAIMON_RESULTS         = local.results_schema_name
      DAIMON_CEM             = try(local.data_source_daimons.daimon_cem, null)
      DAIMON_CEM_RESULTS     = try(local.data_source_daimons.daimon_cem_results, null)
      DAIMON_TEMP            = local.temp_schema_name
    }

    command = "../scripts/add_data_source.sh"
  }

  depends_on = [terraform_data.deployment_atlas_security]
}

resource "terraform_data" "init_synapse_schemas" {
  count = local.is_synapse_data_source && local.daimon_results != null && local.daimon_temp != null ? 1 : 0

  provisioner "local-exec" {
    environment = {
      ADMIN_USERNAME             = local.data_source_config.username
      ADMIN_USER_PASSWORD        = local.data_source_config.password
      SCHEMA_NAME                = local.short_service_id
      SQL_FILE_PATH              = "../sql/init_results_and_temp_schemas.sql"
      SYNAPSE_SERVER             = tostring(regex("(?:jdbc:sqlserver://)(.*)(:?:1433)", local.data_source_config.connection_string)[0])
      SYNAPSE_DATABASE           = tostring(regex("(?:database=)(.*)(:?;user)", local.data_source_config.connection_string)[0])
      RESULTS_SCHEMA_NAME        = local.results_schema_name
      TEMP_SCHEMA_NAME           = local.temp_schema_name
      ORIGIN_RESULTS_SCHEMA_NAME = local.data_source_daimons.daimon_results
    }
    command = "../scripts/synapse_runner.sh"
  }
}
