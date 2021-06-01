locals {
  core_services_vnet_subnets            = cidrsubnets(var.address_space, 4, 4, 4, 4, 4, 4)
  firewall_subnet_address_space         = local.core_services_vnet_subnets[0]
  app_gw_subnet_address_prefix          = local.core_services_vnet_subnets[1]
  bastion_subnet_address_prefix         = local.core_services_vnet_subnets[2]
  web_app_subnet_address_prefix         = local.core_services_vnet_subnets[3]
  shared_services_subnet_address_prefix = local.core_services_vnet_subnets[4]
  aci_subnet_address_prefix             = local.core_services_vnet_subnets[5]
}
