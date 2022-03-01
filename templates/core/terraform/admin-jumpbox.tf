resource "azurerm_network_interface" "jumpbox_nic" {
  name                = "nic-vm-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location

  ip_configuration {
    name                          = "internalIPConfig"
    subnet_id                     = module.network.shared_subnet_id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "random_string" "username" {
  length      = 4
  upper       = true
  lower       = true
  number      = true
  min_numeric = 1
  min_lower   = 1
  special     = false
}

resource "random_password" "password" {
  length           = 16
  lower            = true
  min_lower        = 1
  upper            = true
  min_upper        = 1
  number           = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_virtual_machine" "jumpbox" {
  name                  = "vm-${var.tre_id}"
  resource_group_name   = azurerm_resource_group.core.name
  location              = azurerm_resource_group.core.location
  network_interface_ids = [azurerm_network_interface.jumpbox_nic.id]
  vm_size               = "Standard_B2s"

  delete_os_disk_on_termination = true

  delete_data_disks_on_termination = true

  storage_image_reference {
    publisher = "MicrosoftWindowsDesktop"
    offer     = "windows-10"
    sku       = "20h2-pro-g2"
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

  os_profile_windows_config {
  }

  tags = {
    environment = "staging"
  }
}

resource "azurerm_key_vault_secret" "jumpbox_credentials" {
  name         = "${azurerm_virtual_machine.jumpbox.name}-jumpbox-admin-credentials"
  value        = "${random_string.username.result}\n${random_password.password.result}"
  key_vault_id = azurerm_key_vault.kv.id
}
