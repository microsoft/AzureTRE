locals {

  core_resource_group_name = "rg-${var.tre_id}"

  workspace_short_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.workspace_short_id}"
  workspace_resource_group_name  = "rg-${local.workspace_resource_name_suffix}"
  workspace_vnet_name            = "vnet-${local.workspace_resource_name_suffix}"
  workspace_keyvault_name        = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")

  service_short_id             = substr(var.tre_resource_id, -4, -1)
  service_resource_name_suffix = "${local.workspace_resource_name_suffix}-svc-${local.service_short_id}"

  azuresql_server_name         = "azsql-${local.service_resource_name_suffix}"
  azuresql_administrator_login = "azuresqladmin"
  azuresql_collation           = "SQL_Latin1_General_CP1_CI_AS"

  azuresql_sku = {
    "S1 | 20 DTUs"  = { value = "S1" },
    "S2 | 50 DTUs"  = { value = "S2" },
    "S3 | 100 DTUs" = { value = "S3" },
    "S4 | 200 DTUs" = { value = "S4" },
    "S6 | 400 DTUs" = { value = "S6" },
  }

  azuresql_private_endpoint_name           = "pe-${azurerm_mssql_server.azuresql.name}"
  azuresql_private_service_connection_name = "psc-${azurerm_mssql_server.azuresql.name}"
  azuresql_password_keyvault_secret_name   = "${azurerm_mssql_server.azuresql.name}-administrator-password"

  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
}
