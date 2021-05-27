locals {
  ws_services_vnet_subnets            = cidrsubnets(var.address_space, 4)
  services_subnet_address_prefix      = local.ws_services_vnet_subnets[0]
}
