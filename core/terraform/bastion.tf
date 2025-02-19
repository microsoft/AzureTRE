resource "azurerm_public_ip" "bastion" {
  name                = "pip-bas-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags, zones] }
}

resource "azurerm_bastion_host" "bastion" {
  name                = "bas-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location

  ip_configuration {
    name                 = "configuration"
    subnet_id            = module.network.bastion_subnet_id
    public_ip_address_id = azurerm_public_ip.bastion.id
  }

  sku {
    name = var.bastion_sku
  }

  tags = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}
