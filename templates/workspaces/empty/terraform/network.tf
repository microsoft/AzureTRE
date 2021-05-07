resource "azurerm_virtual_network" "workspace" {
  name                = "vnet-workspace"
  resource_group_name = azurerm_resource_group.workspace.name
  location            = var.location
  address_space       = [var.address_space]
}


resource "azurerm_subnet" "appgw" {
  name                 = "appgwSubnet"
  virtual_network_name = azurerm_virtual_network.workspace.name
  resource_group_name  = azurerm_resource_group.workspace.name
  address_prefixes     = [local.appgw_subnet_address_prefix]
}

resource "azurerm_subnet" "web_app" {
  name                 = "web_appSubnet"
  virtual_network_name = azurerm_virtual_network.workspace.name
  resource_group_name  = azurerm_resource_group.workspace.name
  address_prefixes     = [local.web_app_subnet_address_prefix]
  delegation {
    name = "web_app"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }

}

resource "azurerm_subnet" "services" {
  name                                           = "servicesSubnet"
  virtual_network_name                           = azurerm_virtual_network.workspace.name
  resource_group_name                            = azurerm_resource_group.workspace.name
  address_prefixes                               = [local.services_subnet_address_prefix]
  enforce_private_link_endpoint_network_policies = true
}





resource "azurerm_subnet_network_security_group_association" "services" {
  network_security_group_id = azurerm_network_security_group.workspace.id
  subnet_id                 = azurerm_subnet.services.id
}


resource "azurerm_subnet_network_security_group_association" "web_app" {
  network_security_group_id = azurerm_network_security_group.workspace.id
  subnet_id                 = azurerm_subnet.web_app.id
}

resource "azurerm_network_security_group" "workspace" {
  name                = "nsg-workspace"
  resource_group_name = azurerm_resource_group.workspace.name
  location            = azurerm_resource_group.workspace.location

}


resource "azurerm_network_security_rule" "allow_inbound_web_app_to_services" {

  name = "allow-inbound-web-app-to-services"

  protocol                     = "*"
  source_port_range            = "*"
  destination_port_range       = "*"
  source_address_prefixes      = azurerm_subnet.web_app.address_prefixes
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  access                       = "Allow"
  priority                     = 102
  direction                    = "Inbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "allow_inbound_appgw_to_services" {

  name = "allow-inbound-appgw-to-services"

  protocol                     = "*"
  source_port_range            = "*"
  destination_port_range       = "*"
  source_address_prefixes      = azurerm_subnet.appgw.address_prefixes
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  access                       = "Allow"
  priority                     = 103
  direction                    = "Inbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "allow_inbound_appgw_to_webapp" {

  name = "allow-inbound-appgw-to-webapp"

  protocol                     = "*"
  source_port_range            = "*"
  destination_port_range       = "443"
  source_address_prefixes      = azurerm_subnet.appgw.address_prefixes
  destination_address_prefixes = azurerm_subnet.web_app.address_prefixes
  access                       = "Allow"
  priority                     = 104
  direction                    = "Inbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}



resource "azurerm_network_security_rule" "allow_inbound_within_services" {

  name = "allow-inbound-within-services"

  protocol                     = "*"
  source_port_range            = "*"
  destination_port_range       = "*"
  source_address_prefixes      = azurerm_subnet.services.address_prefixes
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  access                       = "Allow"
  priority                     = 105
  direction                    = "Inbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "allow_inbound_from_bastion_to_services" {

  name = "allow-inbound-from-bastion-to-services"

  protocol                     = "Tcp"
  source_port_range            = "*"
  destination_port_ranges      = ["22", "3389"]
  source_address_prefixes      = data.azurerm_subnet.shared_services_bastion.address_prefixes
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  access                       = "Allow"
  priority                     = 107
  direction                    = "Inbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "deny_all_inbound_override" {

  name = "deny-all-inbound-override"

  protocol                   = "*"
  source_port_range          = "*"
  destination_port_range     = "*"
  source_address_prefix      = "*"
  destination_address_prefix = "*"
  access                     = "Deny"
  priority                   = 900
  direction                  = "Inbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}


resource "azurerm_network_security_rule" "to_internet" {

  name = "to-internet"

  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "443"
  source_address_prefix      = "*"
  destination_address_prefix = "INTERNET"
  access                     = "Allow"
  priority                   = 900
  direction                  = "Outbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "allow_outbound_web_app_to_services" {

  name = "allow-outbound-web-app-to-services"

  protocol                     = "*"
  source_port_range            = "*"
  destination_port_range       = "*"
  source_address_prefixes      = azurerm_subnet.web_app.address_prefixes
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  access                       = "Allow"
  priority                     = 101
  direction                    = "Outbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "allow_outbound_web_app_to_appgw" {

  name = "allow-outbound-webapp-to-appgw"

  protocol                     = "*"
  source_port_range            = "*"
  destination_port_range       = "*"
  source_address_prefixes      = azurerm_subnet.web_app.address_prefixes
  destination_address_prefixes = azurerm_subnet.appgw.address_prefixes
  access                       = "Allow"
  priority                     = 106
  direction                    = "Outbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "allow-outbound-services-to-appgw" {

  name = "allow-outbound-services-to-appgw"

  protocol                     = "*"
  source_port_range            = "*"
  destination_port_range       = "*"
  source_address_prefixes      = azurerm_subnet.services.address_prefixes
  destination_address_prefixes = azurerm_subnet.appgw.address_prefixes
  access                       = "Allow"
  priority                     = 107
  direction                    = "Outbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "deny-outbound-override" {

  name = "deny-outbound-override"

  protocol                   = "*"
  source_port_range          = "*"
  destination_port_range     = "*"
  source_address_prefix      = "*"
  destination_address_prefix = "*"
  access                     = "Deny"
  priority                   = 4096
  direction                  = "Outbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_network_security_rule" "to-shared_services-services" {

  name = "to-shared_services-services"

  protocol                   = "*"
  source_port_range          = "*"
  destination_port_range     = "*"
  source_address_prefix      = "*"
  destination_address_prefix = data.azurerm_subnet.shared_services.address_prefix
  access                     = "Allow"
  priority                   = 120
  direction                  = "Outbound"

  network_security_group_name = azurerm_network_security_group.workspace.name
  resource_group_name         = azurerm_resource_group.workspace.name

}

resource "azurerm_virtual_network_peering" "core-vnet" {
  name                         = "to-core-vnet"
  allow_forwarded_traffic      = false
  allow_gateway_transit        = false
  allow_virtual_network_access = true
  resource_group_name          = azurerm_resource_group.workspace.name
  remote_virtual_network_id    = data.azurerm_virtual_network.core.id
  virtual_network_name         = azurerm_virtual_network.workspace.name
}

resource "azurerm_virtual_network_peering" "workspace-vnet" {
  name                         = "to-${var.workspace_id}-vnet"
  allow_forwarded_traffic      = false
  allow_gateway_transit        = false
  allow_virtual_network_access = true
  resource_group_name          = data.azurerm_resource_group.core.name
  remote_virtual_network_id    = azurerm_virtual_network.workspace.id
  virtual_network_name         = data.azurerm_virtual_network.core.name
}

