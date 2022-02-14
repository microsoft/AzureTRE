resource "azurerm_network_interface" "internal" {
  name                = "internal-nic-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.services.id
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

resource "azurerm_windows_virtual_machine" "windowsvm" {
  name                  = local.vm_name
  location              = data.azurerm_resource_group.ws.location
  resource_group_name   = data.azurerm_resource_group.ws.name
  network_interface_ids = [azurerm_network_interface.internal.id]
  size                  = "Standard_DS1_v2"
  admin_username        = random_string.username.result
  admin_password        = random_password.password.result

  source_image_reference {
    publisher = local.image_ref[var.image].publisher
    offer     = local.image_ref[var.image].offer
    sku       = local.image_ref[var.image].sku
    version   = local.image_ref[var.image].version
  }

  os_disk {
    name                 = "osdisk-${local.vm_name}"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    parent_service_id = var.parent_service_id
  }
}

resource "azurerm_key_vault_secret" "windowsvm_password" {
  name         = "${local.vm_name}-admin-credentials"
  value        = "${random_string.username.result}\n${random_password.password.result}"
  key_vault_id = data.azurerm_key_vault.ws.id
}

resource "azurerm_virtual_machine_extension" "config_script" {
  name                 = "hostname"
  virtual_machine_id   = azurerm_windows_virtual_machine.windowsvm.id
  publisher            = "Microsoft.Azure.Extensions"
  type                 = "CustomScript"
  type_handler_version = "2.0"

  settings = <<SETTINGS
    {
        "script": "${base64encode(templatefile("config_script.ps1", {
          storageAccountName="${azurerm_virtual_machine.windowsvm.name}",
          fileShareName = "${data.azurerm_storage_share.shared_storage.name}",
          storageAccountKeys = "${data.azurerm_storage_account.stg.primary_access_key}"
        }))}"
    }
SETTINGS
}

data "azurerm_resource_group" "base_tre" {
  name = "rg-${var.tre_id}"
}

data "azurerm_storage_account" "stg" {
  name = lower(replace("stg-${var.tre_id}", "-", ""))
  resource_group_name = data.azurerm_resource_group.base_tre.name
}

data "azurerm_storage_share" "shared_storage" {
  name                 = var.shared_storage_name
  storage_account_name = data.azurerm_storage_account.stg.name
}
