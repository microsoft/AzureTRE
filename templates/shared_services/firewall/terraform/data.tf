data "azurerm_subnet" "firewall" {
  name                 = "AzureFirewallSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_subnet" "firewall_management" {
  name                 = "AzureFirewallManagementSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_subnet" "shared" {
  name                 = "SharedSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_subnet" "resource_processor" {
  name                 = "ResourceProcessorSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_subnet" "web_app" {
  name                 = "WebAppSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_subnet" "airlock_processor" {
  name                 = "AirlockProcessorSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_subnet" "airlock_storage" {
  name                 = "AirlockStorageSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_subnet" "airlock_events" {
  name                 = "AirlockEventsSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_resource_group" "rg" {
  name = local.core_resource_group_name
}

data "azurerm_ip_group" "resource_processor" {
  name                = "ipg-resource-processor"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_ip_group" "shared" {
  name                = "ipg-shared"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_ip_group" "web" {
  name                = "ipg-web-app"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_ip_group" "referenced" {
  for_each = toset(distinct(flatten(
    [for collection in concat(local.api_driven_network_rule_collection, local.api_driven_application_rule_collection) :
      [for rule in collection.rules : try(rule.source_ip_groups_in_core, [])]
    ]
  )))
  name                = each.value
  resource_group_name = local.core_resource_group_name
}
