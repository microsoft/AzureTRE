locals {
  core_vnet                      = "vnet-${var.tre_id}"
  short_workspace_id             = substr(var.tre_resource_id, -4, -1)
  core_resource_group_name       = "rg-${var.tre_id}"
  dns_policy_name                = "dnspol-${var.tre_id}"
  workspace_resource_name_suffix = "${var.tre_id}-ws-${local.short_workspace_id}"
  address_spaces                 = jsondecode(base64decode(var.address_spaces))
  vnet_subnets                   = cidrsubnets(local.address_spaces[0], 1, 1)
  services_subnet_address_prefix = local.vnet_subnets[0]
  webapps_subnet_address_prefix  = local.vnet_subnets[1]
  is_separate_subscription       = data.azurerm_client_config.core.subscription_id != data.azurerm_client_config.workspace.subscription_id
  route_table_name               = "rt-${local.workspace_resource_name_suffix}"
  route_table_id                 = local.is_separate_subscription ? azurerm_route_table.rt[0].id : data.azurerm_route_table.rt.id
}
