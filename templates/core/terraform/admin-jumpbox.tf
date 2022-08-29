resource "azurerm_network_interface" "jumpbox_nic" {
  name                = "nic-vm-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  tags                = local.tre_core_tags

  ip_configuration {
    name                          = "internalIPConfig"
    subnet_id                     = module.network.shared_subnet_id
    private_ip_address_allocation = "Dynamic"
  }
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
  resource_group_name        = azurerm_resource_group.core.name
  location                   = azurerm_resource_group.core.location
  network_interface_ids      = [azurerm_network_interface.jumpbox_nic.id]
  size                       = var.admin_jumpbox_vm_sku
  allow_extension_operations = true
  admin_username             = "adminuser"
  admin_password             = random_password.password.result
  tags                       = local.tre_core_tags

  custom_data = base64encode(data.template_file.vm_config.rendered)

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

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_key_vault_secret" "jumpbox_credentials" {
  name         = "${azurerm_windows_virtual_machine.jumpbox.name}-jumpbox-password"
  value        = random_password.password.result
  key_vault_id = azurerm_key_vault.kv.id
  depends_on = [
    azurerm_key_vault_access_policy.deployer
  ]
}
resource "azurerm_virtual_machine_extension" "config_script" {
  name                 = "${azurerm_windows_virtual_machine.jumpbox.name}-vmextension"
  virtual_machine_id   = azurerm_windows_virtual_machine.jumpbox.id
  publisher            = "Microsoft.Compute"
  type                 = "CustomScriptExtension"
  type_handler_version = "1.10"

  settings = <<SETTINGS
    {
      "commandToExecute": "powershell -ExecutionPolicy Unrestricted -NoProfile -NonInteractive -command \"cp c:/azuredata/customdata.bin c:/azuredata/configure.ps1; c:/azuredata/configure.ps1 \""
    }
SETTINGS
}

data "template_file" "vm_config" {
  template = file("${path.module}/admin-jumpbox-configure.ps1")
}

resource "azurerm_virtual_machine_extension" "antimalware" {
  virtual_machine_id         = azurerm_windows_virtual_machine.jumpbox.id
  name                       = "${azurerm_windows_virtual_machine.jumpbox.name}-AntimalwareExtension"
  publisher                  = "Microsoft.Azure.Security"
  type                       = "IaaSAntimalware"
  type_handler_version       = "1.3"
  auto_upgrade_minor_version = true

  settings = jsonencode({
    "AntimalwareEnabled" = true
  })
}
