locals {
    storage_name        = lower(replace("stg${var.workspace_id}${var.service_id}","-",""))
    resource_group_name = "rg-${var.workspace_id}"
    workspace_vnet      = "vnet-${var.workspace_id}"
    shared_subnet       = "ServicesSubnet"
}

data "azurerm_subnet" "ServicesSubnet" {
    name                 = "ServicesSubnet"
    virtual_network_name = local.workspace_vnet
    resource_group_name  = local.resource_group_name
}

data "azurerm_virtual_network" "ws" {
  name                = local.workspace_vnet
  resource_group_name = local.resource_group_name
}
