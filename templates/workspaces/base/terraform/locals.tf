locals {
  #Todo, replace 6 chars with random string
  ws_unique_identifier_suffix    = var.is_legacy_shortened_ws_id ? substr(var.tre_resource_id, -4, -1) : substr(var.tre_resource_id, -6, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.ws_unique_identifier_suffix}"
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, var.is_legacy_shortened_ws_id ? -8 : -10, -1)}", "-", ""))
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, var.is_legacy_shortened_ws_id ? -20 : -22, -1)}")
  redacted_senstive_value        = "REDACTED"
  tre_workspace_tags = {
    tre_id           = var.tre_id
    tre_workspace_id = var.tre_resource_id
  }
}
