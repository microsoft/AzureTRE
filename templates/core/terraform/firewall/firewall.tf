resource "azurerm_public_ip" "fwpip" {
  name                  = "pip-fw-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name   = var.resource_group_name
  location              = var.location
  allocation_method     = "Static"
  sku                   = "Standard"
}

resource "azurerm_firewall" "fw" {
  depends_on            = [azurerm_public_ip.fwpip]
  name                  = "fw-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name   = var.resource_group_name
  location              = var.location
  ip_configuration {
    name        = "fw-ip-configuration"
    subnet_id   = var.firewall_subnet
    public_ip_address_id = azurerm_public_ip.fwpip.id
  }
}

resource "azurerm_route_table" "rt" {
  name                          = "rt-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  disable_bgp_route_propagation = false

  route {
    name           = "DefaultRoute"
    address_prefix = "0.0.0.0/0"
    next_hop_type  = "VirtualAppliance"
    next_hop_in_ip_address = azurerm_firewall.fw.ip_configuration.0.private_ip_address
  }
}

resource "azurerm_subnet_route_table_association" "rt_shared_subnet_association" {
  subnet_id      = var.shared_subnet
  route_table_id = azurerm_route_table.rt.id
}
