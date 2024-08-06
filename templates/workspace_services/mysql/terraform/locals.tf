locals {
  short_service_id               = substr(var.tre_resource_id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  core_resource_group_name       = "rg-${var.tre_id}"
  sql_sku = {
    "B | 4GB 2vCores"   = { value = "B_Standard_B2s" },
    "GP | 8GB 2vCores"  = { value = "GP_Standard_D2ds_v4" },
    "BC | 16GB 2vCores" = { value = "MO_Standard_E2ds_v4" }
  }
  workspace_service_tags = {
    tre_id                   = var.tre_id
    tre_workspace_id         = var.workspace_id
    tre_workspace_service_id = var.tre_resource_id
  }
}
