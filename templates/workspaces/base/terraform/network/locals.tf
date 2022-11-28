locals {
  core_vnet                      = "vnet-${var.tre_id}"
  short_workspace_id             = substr(var.tre_resource_id, -4, -1)
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  address_spaces                 = jsondecode(base64decode(var.address_spaces))
  vnet_subnets                   = cidrsubnets(local.address_spaces[0], 1, 1)
  services_subnet_address_prefix = local.vnet_subnets[0]
  webapps_subnet_address_prefix  = local.vnet_subnets[1]
}
