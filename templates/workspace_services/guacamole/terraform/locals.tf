locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  webapp_name                    = "guacamole-${local.service_resource_name_suffix}"
  core_resource_group_name       = "rg-${var.tre_id}"
  aad_tenant_id                  = data.azurerm_key_vault_secret.aad_tenant_id.value
  issuer                         = "https://login.microsoftonline.com/${local.aad_tenant_id}/v2.0"
  webapp_suffix                  = "azurewebsites.net"
  api_url                        = "https://api-${var.tre_id}.${local.webapp_suffix}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
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

  webapp_access_prefix     = var.is_exposed_externally ? "${var.tre_url}/${var.tre_resource_id}" : "https://${local.webapp_name}.${local.webapp_suffix}"
  webapp_auth_callback_url = "${local.webapp_access_prefix}/oauth2/callback"
}
