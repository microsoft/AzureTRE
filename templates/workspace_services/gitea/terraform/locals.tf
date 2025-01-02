locals {
  short_service_id               = substr(var.id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  storage_name                   = lower(replace("stg${substr(local.service_resource_name_suffix, -8, -1)}", "-", ""))
  webapp_name                    = "gitea-${local.service_resource_name_suffix}"
  core_resource_group_name       = "rg-${var.tre_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  version                        = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  sql_sku = {
    "B | 4GB 2vCores"   = { value = "B_Standard_B2s" },
    "GP | 8GB 2vCores"  = { value = "GP_Standard_D2ds_v4" },
    "BC | 16GB 2vCores" = { value = "MO_Standard_E2ds_v4" }
  }
  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.id
  }
  web_app_diagnostic_categories_enabled = [
    "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs",
    "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs", "AppServiceAntivirusScanAuditLogs"
  ]
  gitea_openid_auth        = "${var.aad_authority_url}/${data.azurerm_key_vault_secret.aad_tenant_id.value}/v2.0"
  cmk_name                 = "tre-encryption-${local.workspace_resource_name_suffix}"
  encryption_identity_name = "id-encryption-${var.tre_id}-${local.short_workspace_id}"
}
