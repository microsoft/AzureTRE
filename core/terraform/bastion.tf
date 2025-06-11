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
  count               = var.deploy_bastion ? 1 : 0
  name                = "bas-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  sku                 = var.bastion_sku
  virtual_network_id  = var.bastion_sku == "Developer" ? module.network.core_vnet_id : null

  ip_configuration {
    name                 = "configuration"
    subnet_id            = module.network.bastion_subnet_id
    public_ip_address_id = azurerm_public_ip.bastion.id
  }

  tags = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}
