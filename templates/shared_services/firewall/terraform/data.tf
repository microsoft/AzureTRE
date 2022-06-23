data "azurerm_subnet" "firewall" {
  name                 = "AzureFirewallSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "shared" {
  name                 = "SharedSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "resource_processor" {
  name                 = "ResourceProcessorSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "web_app" {
  name                 = "WebAppSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "airlock_processor" {
  name                 = "AirlockProcessorSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "airlock_storage" {
  name                 = "AirlockStorageSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "airlock_events" {
  name                 = "AirlockEventsSubnet"
  virtual_network_name = "vnet-${var.tre_id}"

  resource_group_name = local.core_resource_group_name
}

data "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_resource_group" "rg" {
  name = local.core_resource_group_name
}
