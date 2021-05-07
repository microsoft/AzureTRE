
data "azurerm_subscription" "current" {
}

data "azurerm_client_config" "current" {
}

locals {
  storage_account_name = "wsstorage${var.workspace_id}"

  workspace_vnet_subnets         = cidrsubnets(var.address_space, 3, 2, 4)
  appgw_subnet_address_prefix    = local.workspace_vnet_subnets[0]
  appgw_private_ip               = cidrhost(local.appgw_subnet_address_prefix, 5)
  web_app_subnet_address_prefix  = local.workspace_vnet_subnets[1]
  services_subnet_address_prefix = local.workspace_vnet_subnets[2]
}
