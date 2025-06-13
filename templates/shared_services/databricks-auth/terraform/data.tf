data "azurerm_resource_group" "rg" {
  name = local.core_resource_group_name
}

data "azurerm_virtual_network" "core" {
  name                = local.core_virtual_network_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_subnet" "services" {
  name                 = "SharedSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_virtual_network.core.resource_group_name
}

data "azurerm_private_dns_zone" "databricks" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azuredatabricks.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}
