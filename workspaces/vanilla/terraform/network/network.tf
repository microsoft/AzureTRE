resource "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${var.workspace_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.address_space]

  lifecycle { ignore_changes = [ tags ] }
}


resource "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.services_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies = true
}

resource "azurerm_subnet" "webapps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = azurerm_virtual_network.ws.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [local.webapps_subnet_address_prefix]
  # notice that private endpoints do not adhere to NSG rules
  enforce_private_link_endpoint_network_policies = true
  enforce_private_link_service_network_policies = true

  delegation {
    name = "delegation"

    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

data "azurerm_virtual_network" "core" {
  name                = var.core_vnet
  resource_group_name = var.core_resource_group_name
}

resource "azurerm_virtual_network_peering" "ws-core-peer" {
  name                      = "ws-core-peer-${var.tre_id}-ws-${var.workspace_id}"
  resource_group_name       = var.resource_group_name
  virtual_network_name      = azurerm_virtual_network.ws.name
  remote_virtual_network_id = data.azurerm_virtual_network.core.id
}

resource "azurerm_virtual_network_peering" "core-ws-peer" {
  name                      = "core-ws-peer-${var.tre_id}-ws-${var.workspace_id}"
  resource_group_name       = var.core_resource_group_name
  virtual_network_name      = var.core_vnet
  remote_virtual_network_id = azurerm_virtual_network.ws.id
}

data "azurerm_subnet" "shared" {
  resource_group_name  = var.core_resource_group_name
  virtual_network_name = var.core_vnet
  name                 = "SharedSubnet"
}

data "azurerm_subnet" "bastion" {
  resource_group_name  = var.core_resource_group_name
  virtual_network_name = var.core_vnet
  name                 = "AzureBastionSubnet"
}

resource "azurerm_network_security_group" "ws" {
  location            = var.location
  name                = "nsg-ws"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [ tags ] }
}


resource "azurerm_subnet_network_security_group_association" "services" {
  network_security_group_id = azurerm_network_security_group.ws.id
  subnet_id                 = azurerm_subnet.services.id
}

resource "azurerm_network_security_rule" "deny-outbound-override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "deny-outbound-override"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 4096
  protocol                    = "*"
  resource_group_name         = var.resource_group_name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "deny-all-inbound-override" {
  access                      = "Deny"
  destination_address_prefix  = "*"
  destination_port_range      = "*"
  direction                   = "Inbound"
  name                        = "deny-inbound-override"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 900
  protocol                    = "*"
  resource_group_name         = var.resource_group_name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-within-services-subnet" {
  access                      = "Allow"
  destination_port_range      = "*"
  destination_address_prefix  = azurerm_subnet.services.address_prefix
  source_address_prefix       = azurerm_subnet.services.address_prefix
  direction                   = "Inbound"
  name                        = "inbound-within-services-subnet"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 100
  protocol                    = "*"
  resource_group_name         = var.resource_group_name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-outbound-within-services-subnet" {
  access                      = "Allow"
  destination_port_range      = "*"
  destination_address_prefix  = azurerm_subnet.services.address_prefix
  source_address_prefix       = azurerm_subnet.services.address_prefix
  direction                   = "Outbound"
  name                        = "outbound-within-services-subnet"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 100
  protocol                    = "*"
  resource_group_name         = var.resource_group_name
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-outbound-to-shared-services" {
  access                      = "Allow"
  destination_address_prefix  = data.azurerm_subnet.shared.address_prefix
  destination_port_range      = "*"
  direction                   = "Outbound"
  name                        = "to-shared-services"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 110
  protocol                    = "*"
  resource_group_name         = var.resource_group_name
  source_address_prefix       = "*"
  source_port_range           = "*"
}


resource "azurerm_network_security_rule" "allow-outbound-to-internet" {
  access                      = "Allow"
  destination_address_prefix  = "INTERNET"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-internet"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 120
  protocol                    = "Tcp"
  resource_group_name         = var.resource_group_name
  source_address_prefix       = "*"
  source_port_range           = "*"
}


resource "azurerm_network_security_rule" "allow-inbound-from-bastion" {
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
  resource_group_name         = var.resource_group_name
  source_address_prefixes = [
    data.azurerm_subnet.bastion.address_prefix
  ]
  source_port_range = "*"
}

data "azurerm_route_table" "rt" {
  name                = "rt-${var.tre_id}"
  resource_group_name = var.core_resource_group_name
}

resource "azurerm_subnet_route_table_association" "rt_services_subnet_association" {
  route_table_id = data.azurerm_route_table.rt.id
  subnet_id      = azurerm_subnet.services.id
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurewebsites" {
  resource_group_name   = var.core_resource_group_name
  virtual_network_id    = azurerm_virtual_network.ws.id
  private_dns_zone_name = "privatelink.azurewebsites.net"
  name                  = "link-azurewebsites-${local.workspace_resource_name_suffix}"
  registration_enabled  = false

  lifecycle { ignore_changes = [ tags ] }
}
