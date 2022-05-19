locals {
  short_service_id               = substr(var.id, -4, -1)
  short_workspace_id             = substr(var.workspace_id, -4, -1)
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  service_resource_name_suffix   = "${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_service_id}"
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  version                        = replace(replace(replace(data.local_file.version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
  core_resource_group_name       = "rg-${var.tre_id}"
  sql_sku = {
    "GP | 5GB 2vCores" = { value = "GP_Gen5_2" },
    "GP | 5GB 4vCores" = { value = "GP_Gen5_4" },
    "GP | 5GB 6vCores" = { value = "GP_Gen5_6" },
    "GP | 5GB 8vCores" = { value = "GP_Gen5_8" }
  }
}
