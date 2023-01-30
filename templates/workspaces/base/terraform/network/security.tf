resource "azurerm_network_security_group" "ws" {
  location            = var.location
  name                = "nsg-ws"
  resource_group_name = var.ws_resource_group_name
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet_network_security_group_association" "services" {
  network_security_group_id = azurerm_network_security_group.ws.id
  subnet_id                 = azurerm_subnet.services.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet_route_table_association.rt_webapps_subnet_association
  ]
}

resource "azurerm_subnet_network_security_group_association" "webapps" {
  network_security_group_id = azurerm_network_security_group.ws.id
  subnet_id                 = azurerm_subnet.webapps.id
  depends_on = [
    # meant to resolve AnotherOperation errors with one operation in the vnet at a time
    azurerm_subnet_network_security_group_association.webapps
  ]
}

resource "azurerm_network_security_rule" "allow_outbound_to_shared_services" {
  access                       = "Allow"
  destination_address_prefixes = data.azurerm_subnet.shared.address_prefixes
  destination_port_range       = "*"
  direction                    = "Outbound"
  name                         = "to-shared-services"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 110
  protocol                     = "*"
  resource_group_name          = var.ws_resource_group_name
  source_address_prefix        = "*"
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "allow_outbound_from_webapp_to_core_webapp" {
  access                       = "Allow"
  destination_port_range       = "443"
  destination_address_prefixes = data.azurerm_subnet.core_webapps.address_prefixes
  source_address_prefixes      = azurerm_subnet.webapps.address_prefixes
  direction                    = "Outbound"
  name                         = "outbound-workspace-webapps-to-tre-core-webapps"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 130
  protocol                     = "Tcp"
  resource_group_name          = var.ws_resource_group_name
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "allow_inbound_from_bastion" {
  access                       = "Allow"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  destination_port_ranges = [
    "22",
    "3389",
  ]
  direction                   = "Inbound"
  name                        = "allow-inbound-from-bastion"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 110
  protocol                    = "Tcp"
  resource_group_name         = var.ws_resource_group_name
  source_address_prefixes = [
    data.azurerm_subnet.bastion.address_prefix
  ]
  source_port_range = "*"
}

resource "azurerm_network_security_rule" "allow_inbound_from_resourceprocessor" {
  access                       = "Allow"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  destination_port_range       = "443"
  direction                    = "Inbound"
  name                         = "allow-inbound-from-resourceprocessor"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 120
  protocol                     = "Tcp"
  resource_group_name          = var.ws_resource_group_name
  source_address_prefixes = [
    data.azurerm_subnet.resourceprocessor.address_prefix
  ]
  source_port_range = "*"
}


resource "azurerm_network_security_rule" "allow_inbound_from_airlockprocessor" {
  access                       = "Allow"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  destination_port_range       = "443"
  direction                    = "Inbound"
  name                         = "allow-inbound-from-airlockprocessor"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 140
  protocol                     = "Tcp"
  resource_group_name          = var.ws_resource_group_name
  source_address_prefixes = [
    data.azurerm_subnet.airlockprocessor.address_prefix
  ]
  source_port_range = "*"
}

moved {
  from = azurerm_network_security_rule.allow-outbound-to-shared-services
  to   = azurerm_network_security_rule.allow_outbound_to_shared_services
}
moved {
  from = azurerm_network_security_rule.allow-outbound-from-webapp-to-core-webapp
  to   = azurerm_network_security_rule.allow_outbound_from_webapp_to_core_webapp
}
moved {
  from = azurerm_network_security_rule.allow-inbound-from-bastion
  to   = azurerm_network_security_rule.allow_inbound_from_bastion
}
moved {
  from = azurerm_network_security_rule.allow-inbound-from-resourceprocessor
  to   = azurerm_network_security_rule.allow_inbound_from_resourceprocessor
}
moved {
  from = azurerm_network_security_rule.allow-inbound-from-airlockprocessor
  to   = azurerm_network_security_rule.allow_inbound_from_airlockprocessor
}
