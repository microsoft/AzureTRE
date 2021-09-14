
data "azurerm_network_security_group" "ws" {
  name                = "nsg-ws"
  resource_group_name = data.azurerm_resource_group.ws.name
}


resource "azurerm_network_security_rule" "allow-BatchNodeManagement-inbound-29877" {
  access                      = "Allow"
  destination_port_range      = "29877"
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "BatchNodeManagement"
  direction                   = "Inbound"
  name                        = "BatchNodeManagement-inbound-29877"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = 200
  protocol                    = "TCP"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-BatchNodeManagement-inbound-29876" {
  access                      = "Allow"
  destination_port_range      = "29876"
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "BatchNodeManagement"
  direction                   = "Inbound"
  name                        = "BatchNodeManagement-inbound-29876"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = 201
  protocol                    = "TCP"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-AzureMachineLearning-inbound-44224" {
  access                      = "Allow"
  destination_port_range      = "44224"
  destination_address_prefix  = "VirtualNetwork"
  source_address_prefix       = "*"
  direction                   = "Inbound"
  name                        = "AzureMachineLearning-inbound-44224"
  network_security_group_name = data.azurerm_network_security_group.ws.name
  priority                    = 202
  protocol                    = "TCP"
  resource_group_name         = data.azurerm_resource_group.ws.name
  source_port_range           = "*"
}