locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  core_vnet                      = "vnet-${var.tre_id}"
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  workspace_name                 = lower("ml-${substr(local.service_resource_name_suffix, -30, -1)}")
  acr_name                       = lower(replace("acr${substr(local.service_resource_name_suffix, -8, -1)}", "-", ""))
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  storage_name                   = lower(replace("stg${substr(local.service_resource_name_suffix, -8, -1)}", "-", ""))
  tre_workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
  cmk_name                 = "tre-encryption-${local.workspace_resource_name_suffix}"
  encryption_identity_name = "id-encryption-${var.tre_id}-${local.short_workspace_id}"
}
