data "azuread_client_config" "current" {}
data "azurerm_subscription" "primary" {}

## Create secrets
# Note that key vault secrets must match the name (and key vault secrets don't allow underscores)
resource "azurerm_key_vault_secret" "omopPassword" {
  key_vault_id = data.azurerm_key_vault.ws.id
  name         = "omopPassword"
  value        = var.omop_password
}

# # this is assumed to be the bootstrap administrator id
resource "azurerm_key_vault_secret" "bootstrapAdminObjectId" {
  key_vault_id = data.azurerm_key_vault.ws.id
  name         = "bootstrapAdminObjectId"
  value        = data.azuread_client_config.current.object_id
}

#############################
# AZURE STORAGE
#############################

resource "azurerm_storage_account" "omop_sa" {
  name                     = "${var.prefix}${var.environment}omopsa"
  resource_group_name      = data.azurerm_resource_group.ws.name
  location                 = data.azurerm_resource_group.ws.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "vocabularies" {
  name                  = var.cdr_vocab_container_name
  storage_account_name  = azurerm_storage_account.omop_sa.name
  container_access_type = "private"
}


#############################
# APP SERVICE
#############################



# This creates the Broadsea app service definition
resource "azurerm_app_service" "omop_broadsea" {
  name                = "${var.prefix}-${var.environment}-omop-broadsea"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  app_service_plan_id = data.azurerm_app_service_plan.asp_core.id

  site_config {
    app_command_line                     = ""
    linux_fx_version                     = "DOCKER|${data.azurerm_container_registry.mgmt_acr.name}.azurecr.io/${var.broadsea_image}:${var.broadsea_image_tag}" # could be handled through pipeline instead
    always_on                            = true
    acr_use_managed_identity_credentials = true # Connect ACR with MI
  }

  app_settings = {
    "WEBAPI_RELEASE"                      = "2.9.0"
    "WEBAPI_WAR"                          = "WebAPI-2.9.0.war"
    "WEBSITES_PORT"                       = "8080"
    "WEBSITES_CONTAINER_START_TIME_LIMIT" = "1800"
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
    "WEBSITE_HTTPLOGGING_RETENTION_DAYS"  = "7"
    "WEBAPI_SOURCES"                      = "https://${var.prefix}-${var.environment}-omop-broadsea.azurewebsites.net/WebAPI/source"
    "WEBAPI_URL"                          = "https://${var.prefix}-${var.environment}-omop-broadsea.azurewebsites.net/WebAPI"
    "env"                                 = "webapi-mssql"
    "security_origin"                     = "*"
    "datasource.driverClassName"          = "com.microsoft.sqlserver.jdbc.SQLServerDriver"
    # "datasource.url"                                 = "jdbc:sqlserver://${azurerm_mssql_server.omop_sql_server.name}.database.windows.net:1433;database=${azurerm_mssql_database.OHDSI-CDMV5.name};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;Authentication=ActiveDirectoryMsi"
    "datasource.cdm.schema"                          = "cdm"
    "datasource.ohdsi.schema"                        = "webapi"
    "datasource.username"                            = ""
    "datasource.password"                            = ""
    "spring.jpa.properties.hibernate.default_schema" = "webapi"
    "spring.jpa.properties.hibernate.dialect"        = "org.hibernate.dialect.SQLServer2012Dialect"
    # "spring.batch.repository.tableprefix"            = "${azurerm_mssql_database.OHDSI-CDMV5.name}.webapi.BATCH_"
    "flyway.datasource.driverClassName" = "com.microsoft.sqlserver.jdbc.SQLServerDriver"
    # "flyway.datasource.url"                          = "jdbc:sqlserver://${azurerm_mssql_server.omop_sql_server.name}.database.windows.net:1433;database=${azurerm_mssql_database.OHDSI-CDMV5.name};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;Authentication=ActiveDirectoryMsi"
    "flyway.schemas"                  = "webapi"
    "flyway.placeholders.ohdsiSchema" = "webapi"
    "flyway.datasource.username"      = ""
    "flyway.datasource.password"      = ""
    "flyway.locations"                = "classpath:db/migration/sqlserver"
  }

  identity {
    type = "SystemAssigned"
  }

  # connection_string {
  #   name  = "ConnectionStrings:Default"
  #   type  = "SQLServer" # check if this shuld be SQLServer
  #   value = "jdbc:sqlserver://${azurerm_mssql_server.omop_sql_server.name}.database.windows.net:1433;database=${azurerm_mssql_database.OHDSI-CDMV5.name};encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;Authentication=ActiveDirectoryMsi"
  # }
}

# Assign App Service MI ACR Pull
resource "azurerm_role_assignment" "app_service_acr_pull" {
  scope                = data.azurerm_container_registry.mgmt_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_app_service.omop_broadsea.identity[0].principal_id
}

# #############################
# # AZURE SQL
# #############################

# resource "azurerm_mssql_server" "omop_sql_server" {
#   name                         = "${var.prefix}-${var.environment}-omop-sql-server"
#   resource_group_name          = data.azurerm_resource_group.ws.name
#   location                     = data.azurerm_resource_group.ws.location
#   version                      = "12.0"
#   administrator_login          = "omop_admin"
#   administrator_login_password = var.omop_password
#   minimum_tls_version          = "1.2"
#   tags = {
#     environment = var.environment
#   }

#   # https://registry.terraform.io/providers/hashicorp/azurerm/2.90.0/docs/resources/mssql_server#azuread_administrator
#   # Cover this with az cli call?
#   azuread_administrator {
#     login_username = "my-omop-sql-server-admins"
#     object_id      = data.azuread_client_config.current.object_id
#   }
#   # you can access the principal_id e.g. azurerm_mssql_server.omop_sql_server.identity[0].principal_id
#   # and the tenant_id with azurerm_mssql_server.omop_sql_server.identity[0].tenant_id
#   identity {
#     type = "SystemAssigned"
#   }
# }



###
###
### ARCHIVE
###
###

# This creates the plan that the service use
# data "azurerm_app_service_plan" "omop_asp" {
#   name                = "${var.prefix}-${var.environment}-omop-asp"
#   location            = data.azurerm_resource_group.ws.location
#   resource_group_name = data.azurerm_resource_group.ws.name
#   kind                = var.asp_kind_edition
#   reserved            = true

#   sku {
#     tier = var.asp_sku_tier
#     size = var.asp_sku_size
#   }
# }

# resource "azurerm_storage_account" "nada" {
#   name                     = "tireillydebug2"
#   resource_group_name      = data.azurerm_resource_group.ws.name
#   location                 = data.azurerm_resource_group.ws.location
#   account_tier             = "Standard"
#   account_replication_type = "GRS"
# }

# resource "azuread_application" "spomop" {
#   display_name = "sp-for-${var.prefix}-${var.environment}-omop-service-connection"
#   owners       = [sensitive(data.azuread_client_config.current.object_id)]
# }

# resource "azuread_service_principal" "spomop" {
#   application_id = azuread_application.spomop.application_id
#   owners         = [sensitive(data.azuread_client_config.current.object_id)]
# }

# resource "azuread_service_principal_password" "spomop" {
#   service_principal_id = sensitive(data.azuread_service_principal.spomop.id)
# }

# resource "azurerm_role_assignment" "main" {
#   principal_id         = sensitive(data.azuread_service_principal.spomop.id)
#   scope                = sensitive("/subscriptions/${data.azurerm_client_config.current.subscription_id}")
#   role_definition_name = "Owner"
# }





# resource "azurerm_key_vault_secret" "spServiceConnectionObjectId" {
#   key_vault_id = data.azurerm_key_vault.ws.id
#   name         = "spServiceConnectionObjectId"
#   value        = data.azuread_service_principal.spomop.id
# }

# resource "azurerm_key_vault_secret" "vmssManagedIdentityObjectId" {
#   key_vault_id = data.azurerm_key_vault.ws.id
#   name         = "vmssManagedIdentityObjectId"
#   value        = azurerm_linux_virtual_machine_scale_set.vmss.identity[0].principal_id
# }

# resource "azurerm_key_vault_secret" "storageAccountKey" {
#   key_vault_id = data.azurerm_key_vault.ws.id
#   name         = "storageAccountKey"
#   value        = azurerm_storage_account.tfstatesa.primary_access_key
# }

# data "azuread_service_principal" "spomop" {
#   application_id = "c5c5b6ec-651d-42e1-ab61-8ddbea3c6585"
# }

# data "azuread_application" "spomop" {
#   display_name = "OneCSEWeek2022"
# }
