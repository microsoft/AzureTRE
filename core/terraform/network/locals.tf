locals {
  core_services_vnet_subnets = cidrsubnets(var.core_address_space, 4, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4)
  # Addresses examples are based on /22 CIDR
  # .0
  firewall_subnet_address_space = local.core_services_vnet_subnets[0] # .0 - .63
  app_gw_subnet_address_prefix  = local.core_services_vnet_subnets[1] # .64 - .127
  bastion_subnet_address_prefix = local.core_services_vnet_subnets[2] # .128 - .191
  web_app_subnet_address_prefix = local.core_services_vnet_subnets[3] # .192 - .254

  # .1
  shared_services_subnet_address_prefix = local.core_services_vnet_subnets[4] # .0 - .254

  # .2
  airlock_processor_subnet_address_prefix     = local.core_services_vnet_subnets[5] # .0 - .63
  airlock_storage_subnet_address_prefix       = local.core_services_vnet_subnets[6] # .64 - .127
  airlock_events_subnet_address_prefix        = local.core_services_vnet_subnets[7] # .128 - .191
  airlock_notifications_subnet_address_prefix = local.core_services_vnet_subnets[8] # .192 - .254

  # .3
  resource_processor_subnet_address_prefix  = local.core_services_vnet_subnets[9]  # .0 - .63
  firewall_management_subnet_address_prefix = local.core_services_vnet_subnets[10] # .64 - .127
  # FREE = local.core_services_vnet_subnets[11] # .128 - .191
  # FREE = local.core_services_vnet_subnets[12] # .192 - .254

  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }


  private_dns_zone_names = toset([
    "privatelink.queue.core.windows.net",
    "privatelink.table.core.windows.net"
  ])
}
