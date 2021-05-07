data "azurerm_subscription" "current" {
}

data "azurerm_client_config" "current" {
}

locals {
  shared_services_vnet_subnets                   = cidrsubnets(var.shared_services_vnet_address_space, 2, 4, 4, 2, 2)
  firewall_subnet_address_space       = local.shared_services_vnet_subnets[0]
  app_gw_subnet_address_prefix          = local.shared_services_vnet_subnets[1]
  bastion_subnet_address_prefix        = local.shared_services_vnet_subnets[2]
  web_app_subnet_address_prefix         = local.shared_services_vnet_subnets[3]
  shared_services_subnet_address_prefix = local.shared_services_vnet_subnets[4]

  management_api_image_name               = "${var.container_registry_dns_name}/tre-management-api:${var.container_image_tag}"
}
