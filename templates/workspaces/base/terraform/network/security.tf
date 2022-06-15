resource "azurerm_network_security_group" "ws" {
  location            = var.location
  name                = "nsg-ws"
  resource_group_name = var.ws_resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet_network_security_group_association" "services" {
  network_security_group_id = azurerm_network_security_group.ws.id
  subnet_id                 = azurerm_subnet.services.id
}

resource "azurerm_subnet_network_security_group_association" "webapps" {
  network_security_group_id = azurerm_network_security_group.ws.id
  subnet_id                 = azurerm_subnet.webapps.id
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
  resource_group_name         = var.ws_resource_group_name
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
  resource_group_name         = var.ws_resource_group_name
  source_address_prefix       = "*"
  source_port_range           = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-within-services-subnet" {
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  source_address_prefixes      = azurerm_subnet.services.address_prefixes
  direction                    = "Inbound"
  name                         = "inbound-within-services-subnet"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = var.ws_resource_group_name
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "allow-outbound-within-services-subnet" {
  access                       = "Allow"
  destination_port_range       = "*"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  source_address_prefixes      = azurerm_subnet.services.address_prefixes
  direction                    = "Outbound"
  name                         = "outbound-within-services-subnet"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 100
  protocol                     = "*"
  resource_group_name          = var.ws_resource_group_name
  source_port_range            = "*"
}

resource "azurerm_network_security_rule" "allow-outbound-to-shared-services" {
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


resource "azurerm_network_security_rule" "allow-outbound-to-internet" {
  access                      = "Allow"
  destination_address_prefix  = "INTERNET"
  destination_port_range      = "443"
  direction                   = "Outbound"
  name                        = "to-internet"
  network_security_group_name = azurerm_network_security_group.ws.name
  priority                    = 120
  protocol                    = "Tcp"
  resource_group_name         = var.ws_resource_group_name
  source_address_prefix       = "*"
  source_port_range           = "*"
}


resource "azurerm_network_security_rule" "allow-outbound-from-webapp-to-core-webapp" {
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

resource "azurerm_network_security_rule" "allow-outbound-webapps-to-services" {
  access = "Allow"
  destination_port_ranges = [
    "80",
    "443",
    "445",
    "3306",
    "3389",
    "5432",
  ]
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  source_address_prefixes      = azurerm_subnet.webapps.address_prefixes
  direction                    = "Outbound"
  name                         = "outbound-from-services-to-webapps-subnets"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 140
  protocol                     = "Tcp"
  resource_group_name          = var.ws_resource_group_name
  source_port_range            = "*"
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
  resource_group_name         = var.ws_resource_group_name
  source_address_prefixes = [
    data.azurerm_subnet.bastion.address_prefix
  ]
  source_port_range = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-from-resourceprocessor" {
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


resource "azurerm_network_security_rule" "allow-inbound-from-airlockprocessor" {
  access                       = "Allow"
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  destination_port_range       = "443"
  direction                    = "Inbound"
  name                         = "allow-inbound-from-airlockprocessor"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 130
  protocol                     = "Tcp"
  resource_group_name          = var.ws_resource_group_name
  source_address_prefixes = [
    data.azurerm_subnet.airlockprocessor.address_prefix
  ]
  source_port_range = "*"
}

resource "azurerm_network_security_rule" "allow-inbound-from-webapp-to-services" {
  access = "Allow"
  destination_port_ranges = [
    "80",
    "443",
    "445",
    "3306",
    "3389",
    "5432",
  ]
  destination_address_prefixes = azurerm_subnet.services.address_prefixes
  source_address_prefixes      = azurerm_subnet.webapps.address_prefixes
  direction                    = "Inbound"
  name                         = "inbound-from-webapps-to-services-subnets"
  network_security_group_name  = azurerm_network_security_group.ws.name
  priority                     = 130
  protocol                     = "Tcp"
  resource_group_name          = var.ws_resource_group_name
  source_port_range            = "*"
}
