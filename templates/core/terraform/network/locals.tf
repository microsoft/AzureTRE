locals {
  core_services_vnet_subnets               = cidrsubnets(var.address_space, 4, 4, 4, 4, 2, 2 ,2)
  firewall_subnet_address_space            = local.core_services_vnet_subnets[0] # .0 - .62
  app_gw_subnet_address_prefix             = local.core_services_vnet_subnets[1] # .64 - .127
  bastion_subnet_address_prefix            = local.core_services_vnet_subnets[2] # .128 - .191
  web_app_subnet_address_prefix            = local.core_services_vnet_subnets[3] # .192 - .254
  shared_services_subnet_address_prefix    = local.core_services_vnet_subnets[4] # .0 - .254
  aci_subnet_address_prefix                = local.core_services_vnet_subnets[5] # .0 - .254
  resource_processor_subnet_address_prefix = local.core_services_vnet_subnets[6] # .0 - .254
}
