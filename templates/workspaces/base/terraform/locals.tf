locals {
  core_vnet                      = "vnet-${var.tre_id}"
  short_workspace_id             = substr(var.tre_resource_id, -4, -1)
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  storage_name                   = lower(replace("stg${substr(local.workspace_resource_name_suffix, -8, -1)}", "-", ""))
  keyvault_name                  = lower("kv-${substr(local.workspace_resource_name_suffix, -20, -1)}")
  vnet_subnets                   = cidrsubnets(var.address_space, 1, 1)
  services_subnet_address_prefix = local.vnet_subnets[0]
  webapps_subnet_address_prefix  = local.vnet_subnets[1]
  tre_workspace_tags = {
    tre_id           = var.tre_id
    tre_workspace_id = var.tre_resource_id
  }
}
