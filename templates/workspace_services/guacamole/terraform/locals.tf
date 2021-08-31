# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

locals {
  service_id                   = random_string.unique_id.result
  short_workspace_id           = substr(var.workspace_id, -4, -1)
  service_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.service_id}"
  webapp_name                  = "guacamole-${local.service_resource_name_suffix}"
  core_vnet                    = "vnet-${var.tre_id}"
  core_resource_group_name     = "rg-${var.tre_id}"
  issuer                       = "https://login.microsoftonline.com/${var.aad_tenant_id}/v2.0"
  kv_url                       = "https://kv-guac-${var.tre_id}-${local.short_workspace_id}.vault.azure.net"
  api_url                      = "https://api-${var.tre_id}.azurewebsites.net"
}
