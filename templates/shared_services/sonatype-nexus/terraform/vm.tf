resource "azurerm_network_interface" "nexus" {
  name                = "nic-nexus-${var.tre_id}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.shared.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_private_dns_zone" "nexus" {
  name                = "nexus-${var.tre_id}.${data.azurerm_resource_group.rg.location}.cloudapp.azure.com"
  resource_group_name = local.core_resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "nexus_core_vnet" {
  name                  = "nexuslink-core"
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

resource "azurerm_user_assigned_identity" "nexus_msi" {
  name                = "id-nexus-${var.tre_id}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_access_policy" "nexus_msi" {
  key_vault_id = data.azurerm_key_vault.kv.id
  tenant_id    = azurerm_user_assigned_identity.nexus_msi.tenant_id
  object_id    = azurerm_user_assigned_identity.nexus_msi.principal_id

  secret_permissions = ["Get", "Recover"]
}

resource "azurerm_linux_virtual_machine" "nexus" {
  name                            = "nexus-${var.tre_id}"
  resource_group_name             = local.core_resource_group_name
  location                        = data.azurerm_resource_group.rg.location
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
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.nexus_msi.id]
  }

  boot_diagnostics {
    storage_account_uri = data.azurerm_storage_account.nexus.primary_blob_endpoint
  }

  depends_on = [
    azurerm_key_vault_access_policy.nexus_msi,
    azurerm_firewall_application_rule_collection.shared_subnet_nexus
  ]
}

data "template_cloudinit_config" "nexus_config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/cloud-config"
    content      = data.template_file.nexus_bootstrapping.rendered
  }

  part {
    content_type = "text/cloud-config"
    content = jsonencode({
      write_files = [
        {
          content     = file("${path.module}/../scripts/configure_nexus_repos.sh")
          path        = "/home/adminuser/configure_nexus_repos.sh"
          permissions = "0744"
        },
        {
          content     = data.template_file.configure_nexus_ssl.rendered
          path        = "/etc/cron.daily/configure_nexus_ssl.sh"
          permissions = "0755"
        },
        {
          content     = "nexus.skipDefaultRepositories=true"
          path        = "/etc/nexus-data/etc/nexus.properties"
          permissions = "0755"
        },
        {
          content     = file("${path.module}/../scripts/reset_nexus_password.sh")
          path        = "/home/adminuser/reset_nexus_password.sh"
          permissions = "0744"
        }
      ]
    })
  }
}

data "template_file" "nexus_bootstrapping" {
  template = file("${path.module}/cloud-config.yaml")
  vars = {
    nexus_admin_password = random_password.nexus_admin_password.result
  }
}

data "template_file" "configure_nexus_ssl" {
  template = file("${path.module}/../scripts/configure_nexus_ssl.sh")
  vars = {
    msi_id                 = azurerm_user_assigned_identity.nexus_msi.id
    vault_name             = data.azurerm_key_vault.kv.name
    ssl_cert_name          = data.azurerm_key_vault_certificate.nexus_cert.name
    ssl_cert_password_name = data.azurerm_key_vault_secret.nexus_cert_password.name
  }
}
