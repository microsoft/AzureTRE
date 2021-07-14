resource "azurerm_public_ip" "bastion" {
  name                = "pip-bas-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  allocation_method   = "Static"
  sku                 = "Standard"

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_bastion_host" "bastion" {
  name                = "bas-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location

  ip_configuration {
    name                 = "configuration"
    subnet_id            = var.bastion_subnet
    public_ip_address_id = azurerm_public_ip.bastion.id
  }

  lifecycle { ignore_changes = [ tags ] }
}

