locals {
  core_vnet                = "vnet-${var.tre_id}"
  core_resource_group_name = "rg-${var.tre_id}"
  webapp_name              = "gitea-${var.tre_id}"
  storage_account_name     = lower(replace("stg-${var.tre_id}", "-", ""))
  keyvault_name            = "kv-${var.tre_id}"
  version                  = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  gitea_allowed_fqdns_list = distinct(compact(split(",", replace(var.gitea_allowed_fqdns, " ", ""))))
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
  webapp_diagnostic_categories_enabled = [
    "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs", "AppServiceFileAuditLogs",
    "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs", "AppServiceAntivirusScanAuditLogs"
  ]
}
