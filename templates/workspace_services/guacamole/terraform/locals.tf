locals {
  ws_unique_identifier_suffix    = length(var.parent_ws_unique_identifier_suffix) == 0 ? substr(var.workspace_id, -4, -1) : var.parent_ws_unique_identifier_suffix
  svc_unique_identifier_suffix   = length(var.parent_ws_unique_identifier_suffix) <= 4 ? substr(var.tre_resource_id, -4, -1) : substr(var.tre_resource_id, -6, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.ws_unique_identifier_suffix}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.ws_unique_identifier_suffix}-svc-${local.svc_unique_identifier_suffix}"
  webapp_name                    = "guacamole-${local.service_resource_name_suffix}"
  core_resource_group_name       = "rg-${var.tre_id}"
  aad_tenant_id                  = data.azurerm_key_vault_secret.aad_tenant_id.value
  issuer                         = "https://login.microsoftonline.com/${local.aad_tenant_id}/v2.0"
  api_url                        = "https://api-${var.tre_id}.azurewebsites.net"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, length(var.parent_ws_unique_identifier_suffix) <= 4 ? -20 : -22, -1)}")
  image_tag_from_file            = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  image_tag                      = var.image_tag == "" ? local.image_tag_from_file : var.image_tag
  identity_name                  = "id-${local.webapp_name}"
  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
  guacamole_diagnostic_categories_enabled = [
    "AppServiceHTTPLogs", "AppServiceConsoleLogs", "AppServiceAppLogs", "AppServiceFileAuditLogs",
    "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs", "AppServiceAntivirusScanAuditLogs"
  ]
}
