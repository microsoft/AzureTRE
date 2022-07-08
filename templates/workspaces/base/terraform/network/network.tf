resource "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.workspace_resource_name_suffix}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  address_space       = [var.address_space]
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies  = true

  # Eventgrid CAN'T send messages over private endpoints, hence we need to allow service endpoints to the service bus
  # We are using service endpoints + managed identity to send these messaages
  # https://docs.microsoft.com/en-us/azure/event-grid/consume-private-endpoints
  service_endpoints = ["Microsoft.ServiceBus"]
}

resource "azurerm_subnet" "webapps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.ws_resource_group_name
  address_prefixes     = [local.webapps_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies  = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_virtual_network_peering" "ws-core-peer" {
  name                      = "ws-core-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = var.ws_resource_group_name
  virtual_network_name      = azurerm_virtual_network.ws.name
  remote_virtual_network_id = data.azurerm_virtual_network.core.id
}

resource "azurerm_virtual_network_peering" "core-ws-peer" {
  name                      = "core-ws-peer-${local.workspace_resource_name_suffix}"
  resource_group_name       = local.core_resource_group_name
  virtual_network_name      = local.core_vnet
  remote_virtual_network_id = azurerm_virtual_network.ws.id
}

resource "azurerm_subnet_route_table_association" "rt_services_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.services.id
}

resource "azurerm_subnet_route_table_association" "rt_webapps_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.webapps.id
}
