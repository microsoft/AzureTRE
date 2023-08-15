resource "azurerm_network_interface" "nexus" {
  name                = "nic-nexus-${var.tre_id}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name
  tags                = local.tre_shared_service_tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.shared.id
    private_ip_address_allocation = "Dynamic"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "nexus_core_vnet" {
  name                  = "nexuslink-core"
  resource_group_name   = local.core_resource_group_name
  private_dns_zone_name = data.azurerm_private_dns_zone.nexus.name
  virtual_network_id    = data.azurerm_virtual_network.core.id
  tags                  = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_a_record" "nexus_vm" {
  name                = "@"
  zone_name           = data.azurerm_private_dns_zone.nexus.name
  resource_group_name = local.core_resource_group_name
  ttl                 = 300
  records             = [azurerm_linux_virtual_machine.nexus.private_ip_address]
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "random_password" "nexus_vm_password" {
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

resource "random_password" "nexus_admin_password" {
  length           = 16
  lower            = true
  min_lower        = 1
  upper            = true
  min_upper        = 1
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%"
}

resource "azurerm_key_vault_secret" "nexus_vm_password" {
  name         = "nexus-vm-password"
  value        = random_password.nexus_vm_password.result
  key_vault_id = data.azurerm_key_vault.kv.id
  tags         = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "nexus_admin_password" {
  name         = "nexus-admin-password"
  value        = random_password.nexus_admin_password.result
  key_vault_id = data.azurerm_key_vault.kv.id
  tags         = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_user_assigned_identity" "nexus_msi" {
  name                = "id-nexus-${var.tre_id}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = local.core_resource_group_name
  tags                = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_access_policy" "nexus_msi" {
  key_vault_id = data.azurerm_key_vault.kv.id
  tenant_id    = azurerm_user_assigned_identity.nexus_msi.tenant_id
  object_id    = azurerm_user_assigned_identity.nexus_msi.principal_id

  secret_permissions = ["Get", "List"]
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
  tags                            = local.tre_shared_service_tags

  custom_data = data.template_cloudinit_config.nexus_config.rendered

  lifecycle { ignore_changes = [tags] }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  os_disk {
    name                 = "osdisk-nexus-${var.tre_id}"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 64
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.nexus_msi.id]
  }

  boot_diagnostics {
    storage_account_uri = data.azurerm_storage_account.nexus.primary_blob_endpoint
  }

  depends_on = [
    azurerm_key_vault_access_policy.nexus_msi
  ]

  connection {
    type     = "ssh"
    host     = azurerm_network_interface.nexus.private_ip_address
    user     = "adminuser"
    password = random_password.nexus_vm_password.result
    agent    = false
    timeout  = "10m"
  }

  provisioner "file" {
    source      = "${path.module}/../scripts/nexus_repos_config"
    destination = "/tmp/nexus_repos_config"
  }
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
          path        = "/tmp/configure_nexus_repos.sh"
          permissions = "0744"
        },
        {
          content     = file("${path.module}/../scripts/nexus_realms_config.json")
          path        = "/tmp/nexus_realms_config.json"
          permissions = "0744"
        },
        {
          content     = data.template_file.configure_nexus_ssl.rendered
          path        = "/etc/cron.daily/configure_nexus_ssl.sh"
          permissions = "0755"
        },
        {
          content     = "nexus.skipDefaultRepositories=true\n"
          path        = "/etc/nexus-data/etc/nexus.properties"
          permissions = "0755"
        },
        {
          content     = file("${path.module}/../scripts/reset_nexus_password.sh")
          path        = "/tmp/reset_nexus_password.sh"
          permissions = "0744"
        },
        {
          content     = file("${path.module}/../scripts/wait_for_docker.sh")
          path        = "/tmp/wait_for_docker.sh"
          permissions = "0744"
        }
      ]
    })
  }
}

data "template_file" "nexus_bootstrapping" {
  template = file("${path.module}/cloud-config.yaml")
  vars = {
    NEXUS_ADMIN_PASSWORD = random_password.nexus_admin_password.result
  }
}

data "template_file" "configure_nexus_ssl" {
  template = file("${path.module}/../scripts/configure_nexus_ssl.sh")
  vars = {
    MSI_ID        = azurerm_user_assigned_identity.nexus_msi.id
    VAULT_NAME    = data.azurerm_key_vault.kv.name
    SSL_CERT_NAME = data.azurerm_key_vault_certificate.nexus_cert.name
  }
}

resource "azurerm_virtual_machine_extension" "keyvault" {
  virtual_machine_id         = azurerm_linux_virtual_machine.nexus.id
  name                       = "${azurerm_linux_virtual_machine.nexus.name}-KeyVault"
  publisher                  = "Microsoft.Azure.KeyVault"
  type                       = "KeyVaultForLinux"
  type_handler_version       = "2.0"
  auto_upgrade_minor_version = true
  tags                       = local.tre_shared_service_tags

  settings = jsonencode({
    "secretsManagementSettings" : {
      "pollingIntervalInS" : "3600",
      "requireInitialSync" : true,
      "observedCertificates" : [
        data.azurerm_key_vault_certificate.nexus_cert.versionless_secret_id
      ]
    }
    "authenticationSettings" : {
      "msiEndpoint" : "http://169.254.169.254/metadata/identity",
      "msiClientId" : azurerm_user_assigned_identity.nexus_msi.client_id
    }
  })

  lifecycle { ignore_changes = [tags] }
}
