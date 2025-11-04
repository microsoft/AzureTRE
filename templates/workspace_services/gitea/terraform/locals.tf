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
  asg-block-external-gitea       = "asg-block-external-gitea-ws-${local.short_workspace_id}"
  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.id
  }
  web_app_diagnostic_categories_enabled = [
    "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs", "AppServiceFileAuditLogs",
    "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs", "AppServiceAntivirusScanAuditLogs"
  ]

  rsv_name          = "rsv-${local.workspace_resource_name_suffix}"
  rsv_policy_name   = "rsv-policy-${local.service_resource_name_suffix}"
  rsv_resource_type = "Microsoft.RecoveryServices/vaults"
  resource_list     = jsondecode(data.azapi_resource_action.ds.output).value
  rsv               = [for rsv in local.resource_list : rsv.name if lower(rsv.name) == lower(local.rsv_name) && lower(rsv.type) == lower(local.rsv_resource_type)]
  enableBackup      = (local.rsv != null || local.rsv != []) && contains(local.rsv, local.rsv_name) ? true : false
}
