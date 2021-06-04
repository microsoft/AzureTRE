resource "azurerm_public_ip" "fwpip" {
  name                  = "pip-fw-${var.tre_id}"
  resource_group_name   = var.resource_group_name
  location              = var.location
  allocation_method     = "Static"
  sku                   = "Standard"
}

resource "azurerm_firewall" "fw" {
  depends_on            = [azurerm_public_ip.fwpip]
  name                  = "fw-${var.tre_id}"
  resource_group_name   = var.resource_group_name
  location              = var.location
  ip_configuration {
    name        = "fw-ip-configuration"
    subnet_id   = var.firewall_subnet
    public_ip_address_id = azurerm_public_ip.fwpip.id
  }
}

