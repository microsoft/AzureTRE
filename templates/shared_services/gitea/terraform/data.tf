data "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_app_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_virtual_network" "core" {
  name                = var.core_vnet
  resource_group_name = var.core_resource_group_name
}

data "azurerm_subnet" "shared" {
  resource_group_name  = var.core_resource_group_name
  virtual_network_name = var.core_vnet
  name                 = "SharedSubnet"
}