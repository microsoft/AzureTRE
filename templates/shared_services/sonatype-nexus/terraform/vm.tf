resource "azurerm_network_interface" "nexus" {
  name                = "internal-nic-nexus-${var.tre_id}"
  location            = var.location
  resource_group_name = local.core_resource_group_name

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.shared.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_private_dns_zone" "nexus" {
  name                = "nexus-${var.tre_id}.${var.location}.cloudapp.azure.com"
  resource_group_name = local.core_resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "nexus" {
  name                  = "nexus"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.nexus.name
  virtual_network_id    = data.azurerm_virtual_network.core.id
}

resource "azurerm_private_dns_a_record" "nexus_vm" {
  name                = "@"
  zone_name           = azurerm_private_dns_zone.nexus.name
  resource_group_name = local.core_resource_group_name
  ttl                 = 300
  records             = [azurerm_linux_virtual_machine.nexus.private_ip_address]
}

resource "random_password" "nexus_vm_password" {
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

resource "random_password" "nexus_admin_password" {
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

resource "azurerm_key_vault_secret" "nexus_vm_password" {
  name         = "nexus-vm-password"
  value        = random_password.nexus_vm_password.result
  key_vault_id = data.azurerm_key_vault.kv.id
}

resource "azurerm_key_vault_secret" "nexus_admin_password" {
  name         = "nexus-admin-password"
  value        = random_password.nexus_admin_password.result
  key_vault_id = data.azurerm_key_vault.kv.id
}

resource "azurerm_linux_virtual_machine" "nexus" {
  name                            = "nexus-${var.tre_id}"
  resource_group_name             = local.core_resource_group_name
  location                        = var.location
  network_interface_ids           = [azurerm_network_interface.nexus.id]
  size                            = "Standard_B2s"
  disable_password_authentication = false
  admin_username                  = "adminuser"
  admin_password                  = random_password.nexus_vm_password.result

  custom_data = data.template_cloudinit_config.nexus_config.rendered

  lifecycle { ignore_changes = [tags] }

  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }

  os_disk {
    name                 = "osdisk-nexus-${var.tre_id}"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  identity {
    type = "SystemAssigned"
  }

  boot_diagnostics {
    storage_account_uri = data.azurerm_storage_account.nexus.primary_blob_endpoint
  }
}

data "template_cloudinit_config" "nexus_config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content      = data.template_file.nexus_config.rendered
  }
}

data "template_file" "nexus_config" {
  template = file("${path.module}/cloud-config.yaml")
  vars = {
    nexus_admin_password = random_password.nexus_admin_password.result
  }
}
