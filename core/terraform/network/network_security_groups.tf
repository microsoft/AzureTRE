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

  lifecycle { ignore_changes = [tags] }
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

  lifecycle { ignore_changes = [tags] }
}

# Network security group with only default security rules
# See https://docs.microsoft.com/azure/virtual-network/network-security-groups-overview#default-security-rules
resource "azurerm_network_security_group" "default_rules" {
  name                = "nsg-default-rules"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}
