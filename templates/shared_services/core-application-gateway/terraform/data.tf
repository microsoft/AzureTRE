data "azurerm_resource_group" "core" {
  name = local.core_resource_group_name
}

data "azurerm_public_ip" "agw" {
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_user_assigned_identity" "agw" {
  name                = "id-agw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_storage_account" "staticweb" {
  name                = local.staticweb_storage_name
  resource_group_name = local.core_resource_group_name
}

data "azurerm_linux_web_app" "api" {
  name                = "api-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "agw" {
  name                 = "AppGwSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}
