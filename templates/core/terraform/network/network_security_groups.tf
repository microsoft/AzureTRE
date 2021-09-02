# Network Security Group for Azure Bastion
# See https://docs.microsoft.com/en-us/azure/bastion/bastion-nsg
resource "azurerm_network_security_group" "bastion" {
  name                = "nsg-bastion-subnet"
  location            = var.location
  resource_group_name = var.resource_group_name

  security_rule {
    name                       = "BastionInboundAllowInternet"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "BastionInboundAllowGatewayManager"
    priority                   = 4001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "GatewayManager"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "BastionInboundAllowAzureLoadBalancer"
    priority                   = 4002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "BastionInboundAllowHostCommunication"
    priority                   = 4003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_ranges    = ["5701", "8080"]
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  #security_rule {
  #  name                       = "bastion-inbound-deny-all"
  #  priority                   = 4010
  #  direction                  = "Inbound"
  #  access                     = "Deny"
  #  protocol                   = "*"
  #  source_port_range          = "*"
  #  destination_port_range     = "*"
  #  source_address_prefix      = "*"
  #  destination_address_prefix = "*"
  #}

  security_rule {
    name                       = "BastionOutboundAllowSshRdp"
    priority                   = 4020
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_ranges    = ["22", "3389"]
    source_address_prefix      = "*"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "BastionOutboundAllowAzureCloud"
    priority                   = 4021
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "AzureCloud"
  }

  security_rule {
    name                       = "BastionOutboundAllowHostCommunication"
    priority                   = 4022
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_ranges    = ["5701", "8080"]
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "BastionOutboundAllowGetSessionInformation"
    priority                   = 4023
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  #security_rule {
  #  name                       = "bastion-outbound-deny-all"
  #  priority                   = 4030
  #  direction                  = "Outbound"
  #  access                     = "Deny"
  #  protocol                   = "*"
  #  source_port_range          = "*"
  #  destination_port_range     = "*"
  #  source_address_prefix      = "*"
  #  destination_address_prefix = "*"
  #}
}

resource "azurerm_subnet_network_security_group_association" "bastion" {
  subnet_id                 = azurerm_subnet.bastion.id
  network_security_group_id = azurerm_network_security_group.bastion.id
}

resource "azurerm_network_security_group" "web_app" {
  name                = "nsg-web-app-subnet"
  location            = var.location
  resource_group_name = var.resource_group_name

  # TODO: The real rules - this is just a test rule
  security_rule {
    name                       = "webapp-inbound-allow-virtualnetwork"
    priority                   = 3900
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }
}

resource "azurerm_subnet_network_security_group_association" "web_app" {
  subnet_id                 = azurerm_subnet.web_app.id
  network_security_group_id = azurerm_network_security_group.web_app.id
}

# Test multi-association
resource "azurerm_subnet_network_security_group_association" "resource_processor" {
  subnet_id                 = azurerm_subnet.resource_processor.id
  network_security_group_id = azurerm_network_security_group.web_app.id
}
