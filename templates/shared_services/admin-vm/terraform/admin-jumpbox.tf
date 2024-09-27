resource "azurerm_network_interface" "jumpbox_nic" {
  name                = "nic-vm-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  tags                = local.tre_shared_service_tags

  ip_configuration {
    name                          = "internalIPConfig"
    subnet_id                     = data.azurerm_subnet.shared.id
    private_ip_address_allocation = "Dynamic"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "random_password" "password" {
  length           = 16
  lower            = true
  min_lower        = 1
  upper            = true
  min_upper        = 1
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_windows_virtual_machine" "jumpbox" {
  name                       = "vm-${var.tre_id}"
  resource_group_name        = data.azurerm_resource_group.rg.name
  location                   = data.azurerm_resource_group.rg.location
  network_interface_ids      = [azurerm_network_interface.jumpbox_nic.id]
  size                       = var.admin_jumpbox_vm_sku
  allow_extension_operations = true
  admin_username             = "adminuser"
  admin_password             = random_password.password.result
  tags                       = local.tre_shared_service_tags

  source_image_reference {
    publisher = "MicrosoftWindowsDesktop"
    offer     = "windows-10"
    sku       = "win10-21h2-pro-g2"
    version   = "latest"
  }

  os_disk {
    name                 = "vm-dsk-${var.tre_id}"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "jumpbox_credentials" {
  name         = "${azurerm_windows_virtual_machine.jumpbox.name}-jumpbox-password"
  value        = random_password.password.result
  key_vault_id = data.azurerm_key_vault.keyvault.id
  tags         = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_virtual_machine_extension" "antimalware" {
  virtual_machine_id         = azurerm_windows_virtual_machine.jumpbox.id
  name                       = "${azurerm_windows_virtual_machine.jumpbox.name}-AntimalwareExtension"
  publisher                  = "Microsoft.Azure.Security"
  type                       = "IaaSAntimalware"
  type_handler_version       = "1.3"
  auto_upgrade_minor_version = true
  tags                       = local.tre_shared_service_tags

  settings = jsonencode({
    "AntimalwareEnabled" = true
  })

  lifecycle { ignore_changes = [tags] }
}
