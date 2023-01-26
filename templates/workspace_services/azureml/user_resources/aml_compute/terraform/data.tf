data "azurerm_resource_group" "ws" {
  name = "rg-${local.workspace_resource_name_suffix}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.workspace_resource_name_suffix}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "aml" {
  name                 = "AMLSubnet${local.short_service_id}"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

data "azurerm_machine_learning_workspace" "workspace" {
  name                = local.aml_workspace_name
  resource_group_name = data.azurerm_resource_group.ws.name
}
