locals {
  core_vnet                      = "vnet-${var.tre_id}"
  core_resource_group_name       = "rg-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${var.ws_unique_identifier_suffix}"
  address_spaces                 = jsondecode(base64decode(var.address_spaces))
  vnet_subnets                   = cidrsubnets(local.address_spaces[0], 1, 1)
  services_subnet_address_prefix = local.vnet_subnets[0]
  webapps_subnet_address_prefix  = local.vnet_subnets[1]
}
