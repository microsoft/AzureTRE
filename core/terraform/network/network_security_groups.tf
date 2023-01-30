# Network security group for Azure Bastion subnet
# See https://docs.microsoft.com/azure/bastion/bastion-nsg
resource "azurerm_network_security_group" "bastion" {
  name                = "nsg-bastion-subnet"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  security_rule {
    name                       = "AllowInboundInternet"
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
    name                       = "AllowInboundGatewayManager"
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
    name                       = "AllowInboundAzureLoadBalancer"
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
    name                       = "AllowInboundHostCommunication"
    priority                   = 4003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_ranges    = ["5701", "8080"]
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "AllowOutboundSshRdp"
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
    name                       = "AllowOutboundAzureCloud"
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
    name                       = "AllowOutboundHostCommunication"
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
    name                       = "AllowOutboundGetSessionInformation"
    priority                   = 4023
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  security_rule {
    name                       = "AllowOutboundSshRdpTREAddressSpace"
    priority                   = 4024
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_ranges    = ["22", "3389"]
    source_address_prefix      = "*"
    destination_address_prefix = var.tre_address_space
  }
}

resource "azurerm_subnet_network_security_group_association" "bastion" {
  subnet_id                 = azurerm_subnet.bastion.id
  network_security_group_id = azurerm_network_security_group.bastion.id
  # depend on the last subnet we created in the vnet
  depends_on = [azurerm_subnet.firewall_management]
}

# Network security group for Application Gateway
# See https://docs.microsoft.com/azure/application-gateway/configuration-infrastructure#network-security-groups
resource "azurerm_network_security_group" "app_gw" {
  name                = "nsg-app-gw"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  security_rule {
    name                       = "AllowInboundGatewayManager"
    priority                   = 3800
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "65200-65535"
    source_address_prefix      = "GatewayManager"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowInboundInternet"
    priority                   = 3801
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "app_gw" {
  subnet_id                 = azurerm_subnet.app_gw.id
  network_security_group_id = azurerm_network_security_group.app_gw.id
  depends_on                = [azurerm_subnet_network_security_group_association.bastion]
}

# Network security group with only default security rules
# See https://docs.microsoft.com/azure/virtual-network/network-security-groups-overview#default-security-rules
resource "azurerm_network_security_group" "default_rules" {
  name                = "nsg-default-rules"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  security_rule {
    name                       = "AllowTREAddressSpaceInbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = var.tre_address_space
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "AllowTREAddressSpaceOutbound"
    priority                   = 4001
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = var.tre_address_space
  }
}

resource "azurerm_subnet_network_security_group_association" "shared" {
  subnet_id                 = azurerm_subnet.shared.id
  network_security_group_id = azurerm_network_security_group.default_rules.id
  depends_on                = [azurerm_subnet_network_security_group_association.app_gw]
}

resource "azurerm_subnet_network_security_group_association" "web_app" {
  subnet_id                 = azurerm_subnet.web_app.id
  network_security_group_id = azurerm_network_security_group.default_rules.id
  depends_on                = [azurerm_subnet_network_security_group_association.shared]
}

resource "azurerm_subnet_network_security_group_association" "resource_processor" {
  subnet_id                 = azurerm_subnet.resource_processor.id
  network_security_group_id = azurerm_network_security_group.default_rules.id
  depends_on                = [azurerm_subnet_network_security_group_association.web_app]
}

resource "azurerm_subnet_network_security_group_association" "airlock_processor" {
  subnet_id                 = azurerm_subnet.airlock_processor.id
  network_security_group_id = azurerm_network_security_group.default_rules.id
  depends_on                = [azurerm_subnet_network_security_group_association.resource_processor]
}

resource "azurerm_subnet_network_security_group_association" "airlock_storage" {
  subnet_id                 = azurerm_subnet.airlock_storage.id
  network_security_group_id = azurerm_network_security_group.default_rules.id
  depends_on                = [azurerm_subnet_network_security_group_association.airlock_processor]
}

resource "azurerm_subnet_network_security_group_association" "airlock_events" {
  subnet_id                 = azurerm_subnet.airlock_events.id
  network_security_group_id = azurerm_network_security_group.default_rules.id
  depends_on                = [azurerm_subnet_network_security_group_association.airlock_storage]
}

resource "azurerm_subnet_network_security_group_association" "airlock_notification" {
  subnet_id                 = azurerm_subnet.airlock_notification.id
  network_security_group_id = azurerm_network_security_group.default_rules.id
  depends_on                = [azurerm_subnet_network_security_group_association.airlock_events]
}
