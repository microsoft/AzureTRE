# Azure Provider source and version being used
terraform {
  required_providers {
    azapi = {
      source  = "Azure/azapi"
      version = "~> 1.9.0"
    }
  }
}

resource "azurerm_public_ip" "virtual_network_gateway" {
  name                = "pip-vng-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags, zones] }
}

# There should already exist this route table. However, we must update it,
# so that traffic is routed through the Virtual network gateway.
resource "azapi_update_resource" "rt" {
  type        = "Microsoft.Network/routeTables@2023-05-01"
  resource_id = data.azurerm_route_table.rt.id

  body = jsonencode({
    properties = {
      disableBgpRoutePropagation = true
    }
  })
}

resource "azurerm_route_table" "virtual_network_gateway" {
  name                          = "rt-vng-${var.tre_id}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  disable_bgp_route_propagation = false
  tags                          = local.tre_core_tags

  route {
    name           = "route-WebAppSubnet"
    address_prefix = data.azurerm_subnet.web_app.address_prefixes[0]
    next_hop_type  = "VirtualAppliance"
    next_hop_in_ip_address = data.azurerm_firewall.fw.ip_configuration[0].private_ip_address
  }

  route {
    name           = "route-SharedSubnet"
    address_prefix = data.azurerm_subnet.shared.address_prefixes[0]
    next_hop_type  = "VirtualAppliance"
    next_hop_in_ip_address = data.azurerm_firewall.fw.ip_configuration[0].private_ip_address
  }

  route {
    name           = "route-AirlockStorageSubnet"
    address_prefix = data.azurerm_subnet.airlock_storage.address_prefixes[0]
    next_hop_type  = "VirtualAppliance"
    next_hop_in_ip_address = data.azurerm_firewall.fw.ip_configuration[0].private_ip_address
  }

  route {
    name           = "route-AirlockEventsSubnet"
    address_prefix = data.azurerm_subnet.airlock_events.address_prefixes[0]
    next_hop_type  = "VirtualAppliance"
    next_hop_in_ip_address = data.azurerm_firewall.fw.ip_configuration[0].private_ip_address
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [var.gateway_subnet_address_prefix]
}

resource "azurerm_subnet_route_table_association" "gateway_route_table" {
  subnet_id      = azurerm_subnet.gateway.id
  route_table_id = azurerm_route_table.virtual_network_gateway.id
}

resource "azurerm_virtual_network_gateway" "virtual_network_gateway" {
  name                = "vng-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  type     = "ExpressRoute"

  active_active = false
  enable_bgp    = false
  sku           = "Standard"

  ip_configuration {
    public_ip_address_id          = azurerm_public_ip.virtual_network_gateway.id
    subnet_id                     = azurerm_subnet.gateway.id
  }
}
