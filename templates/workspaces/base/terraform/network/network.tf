resource "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.workspace_resource_name_suffix}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  address_space       = local.address_spaces
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  private_endpoint_network_policies             = "Disabled"
  private_link_service_network_policies_enabled = true
}

resource "azurerm_subnet" "webapps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.webapps_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  private_endpoint_network_policies             = "Disabled"
  private_link_service_network_policies_enabled = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet.services
  ]
}

resource "azurerm_virtual_network_peering" "ws_core_peer" {
  name                      = "ws-core-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = var.ws_resource_group_name
  virtual_network_name      = azurerm_virtual_network.ws.name
  remote_virtual_network_id = data.azurerm_virtual_network.core.id

  triggers = {
    remote_address_space = join(",", data.azurerm_virtual_network.core.address_space)
  }

  # meant to resolve AnotherOperation errors with one operation in the vnet at a time
  depends_on = [
    azurerm_subnet.webapps
  ]
}

moved {
  from = azurerm_virtual_network_peering.ws-core-peer
  to   = azurerm_virtual_network_peering.ws_core_peer
}

resource "azurerm_virtual_network_peering" "core_ws_peer" {
  provider = azurerm.core
  name                      = "core-ws-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = local.core_resource_group_name
  virtual_network_name      = local.core_vnet
  remote_virtual_network_id = azurerm_virtual_network.ws.id

  triggers = {
    remote_address_space = join(",", azurerm_virtual_network.ws.address_space)
  }

  # meant to resolve AnotherOperation errors with one operation in the vnet at a time
  depends_on = [
    azurerm_virtual_network_peering.ws_core_peer
  ]

}

moved {
  from = azurerm_virtual_network_peering.core-ws-peer
  to   = azurerm_virtual_network_peering.core_ws_peer
}

resource "azurerm_subnet_route_table_association" "rt_services_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.services.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_virtual_network_peering.core_ws_peer
  ]
}


resource "azurerm_subnet_route_table_association" "rt_webapps_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.webapps.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet_route_table_association.rt_services_subnet_association
  ]
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.6.0"
  arm_environment = var.arm_environment
}
