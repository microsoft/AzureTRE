locals {
  short_service_id                = substr(var.tre_resource_id, -4, -1)
  short_workspace_id              = substr(var.workspace_id, -4, -1)
  core_resource_group_name        = "rg-${var.tre_id}"
  workspace_resource_name_suffix  = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix    = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  webapp_name                     = "mlflow-${local.service_resource_name_suffix}"
  postgresql_server_name          = "mlflow-${local.service_resource_name_suffix}"
  keyvault_name                   = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                    = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  shared_storage_share            = "vm-shared-storage"
  mlflow_artefacts_container_name = "mlartefacts"
  image_name                      = "mlflow-server"
  image_tag                       = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  tre_workspace_service_tags = merge(
    var.tags, {
      tre_id                   = var.tre_id
      tre_workspace_id         = var.workspace_id
      tre_workspace_service_id = var.tre_resource_id
    }
  )
  web_app_diagnostic_categories_enabled = [
    "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs", "AppServiceFileAuditLogs",
    "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs", "AppServiceAntivirusScanAuditLogs"
  ]
  identity_name = "id-${local.webapp_name}"
}
