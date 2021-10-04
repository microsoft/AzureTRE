data "azurerm_subscription" "current" {}

resource "azurerm_network_interface" "jumpbox-nic" {
  name                = "nic-vm-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location

  ip_configuration {
    name                          = "internalIPConfig"
    subnet_id                     = var.shared_subnet
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_virtual_machine" "jumpbox" {
  name                = "vm-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  network_interface_ids = [azurerm_network_interface.jumpbox-nic.id]
  vm_size               = "Standard_DS1_v2"

  delete_os_disk_on_termination = true

  delete_data_disks_on_termination = true

  storage_image_reference {
    publisher = "MicrosoftWindowsDesktop"
    offer     = "windows-10"
    sku       = "21h1-pro-g2"
    version   = "latest"
  }
  storage_os_disk {
    name              = "vm-dsk-${var.tre_id}"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }
  os_profile {
    computer_name  = "vm-${var.tre_id}"
    admin_username = random_string.username.result
    admin_password = random_password.password.result
  }
  tags = {
    environment = "staging"
  }
}

resource "azurerm_key_vault_secret" "jumpbox-credentials" {
  name         = "${azurerm_virtual_machine.jumpbox.name}-admin-credentials"
  value        = "${random_string.username.result}\n${random_password.password.result}"
  key_vault_id = var.keyvault_id
}