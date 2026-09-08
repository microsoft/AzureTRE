resource "azurerm_subnet" "aci" {
  name                            = "ACI-${var.tre_resource_id}"
  resource_group_name             = data.azurerm_resource_group.ws.name
  virtual_network_name            = data.azurerm_virtual_network.ws.name
  address_prefixes                = [var.address_space]
  default_outbound_access_enabled = false
  service_endpoints               = ["Microsoft.Storage"]

  delegation {
    name = "aci"

    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet_network_security_group_association" "aci" {
  subnet_id                 = azurerm_subnet.aci.id
  network_security_group_id = data.azurerm_subnet.services.network_security_group_id
}

resource "azurerm_subnet_route_table_association" "aci" {
  subnet_id      = azurerm_subnet.aci.id
  route_table_id = data.azurerm_subnet.services.route_table_id
}
