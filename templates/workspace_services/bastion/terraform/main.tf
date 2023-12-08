resource "azurerm_public_ip" "bastion" {
  name                = "${local.bastion_name}-pip"
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location

  allocation_method = "Static"
  sku               = "Standard"
}

resource "azurerm_bastion_host" "bastion" {
  name                = local.bastion_name
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location

  sku                    = "Standard"
  copy_paste_enabled     = true
  file_copy_enabled      = true
  ip_connect_enabled     = false
  shareable_link_enabled = false
  tunneling_enabled      = true // Required for native client support
  scale_units            = var.bastion_scale_units

  ip_configuration {
    name                 = "ipconfig"
    subnet_id            = azurerm_subnet.bastion.id
    public_ip_address_id = azurerm_public_ip.bastion.id
  }
}
