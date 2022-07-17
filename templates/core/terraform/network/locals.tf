locals {
  core_services_vnet_subnets = cidrsubnets(var.core_address_space, 4, 4, 4, 4, 2, 4, 4, 4, 4, 2)
  # .1
  firewall_subnet_address_space = local.core_services_vnet_subnets[0] # .0 - .63
  app_gw_subnet_address_prefix  = local.core_services_vnet_subnets[1] # .64 - .127
  bastion_subnet_address_prefix = local.core_services_vnet_subnets[2] # .128 - .191
  web_app_subnet_address_prefix = local.core_services_vnet_subnets[3] # .192 - .254

  # .2
  shared_services_subnet_address_prefix = local.core_services_vnet_subnets[4] # .0 - .254

  # replacing the aci
  airlock_processor_subnet_address_prefix     = local.core_services_vnet_subnets[5] # .0 - .63
  airlock_storage_subnet_address_prefix       = local.core_services_vnet_subnets[6] # .64 - .127
  airlock_events_subnet_address_prefix        = local.core_services_vnet_subnets[7] # .128 - .191
  airlock_notifications_subnet_address_prefix = local.core_services_vnet_subnets[8] # .128 - .191

  # .3
  resource_processor_subnet_address_prefix = local.core_services_vnet_subnets[9] # .0 - .254

  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }
}
