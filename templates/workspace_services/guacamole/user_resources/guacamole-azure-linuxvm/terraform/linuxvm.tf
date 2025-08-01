resource "azurerm_network_interface" "internal" {
  name                = "internal-nic-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_user_resources_tags
  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.services.id
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

resource "azurerm_linux_virtual_machine" "linuxvm" {
  name                            = local.vm_name
  location                        = data.azurerm_resource_group.ws.location
  resource_group_name             = data.azurerm_resource_group.ws.name
  network_interface_ids           = [azurerm_network_interface.internal.id]
  size                            = local.vm_sizes[var.vm_size]
  disable_password_authentication = false
  admin_username                  = local.admin_username
  admin_password                  = random_password.password.result
  encryption_at_host_enabled      = true
  secure_boot_enabled             = local.secure_boot_enabled
  vtpm_enabled                    = local.vtpm_enabled

  custom_data = data.template_cloudinit_config.config.rendered

  # set source_image_id/reference depending on the config for the selected image
  source_image_id = local.selected_image_source_id
  dynamic "source_image_reference" {
    for_each = local.selected_image_source_refs
    content {
      publisher = source_image_reference.value["publisher"]
      offer     = source_image_reference.value["offer"]
      sku       = source_image_reference.value["sku"]
      version   = source_image_reference.value["version"]
    }
  }

  os_disk {
    name                   = "osdisk-${local.vm_name}"
    caching                = "ReadWrite"
    storage_account_type   = "StandardSSD_LRS"
    disk_encryption_set_id = var.enable_cmk_encryption ? azurerm_disk_encryption_set.linuxvm_disk_encryption[0].id : null
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tre_user_resources_tags

  # ignore changes to secure_boot_enabled and vtpm_enabled as these are destructive
  # (may be allowed once https://github.com/hashicorp/terraform-provider-azurerm/issues/25808 is fixed)
  #
  lifecycle { ignore_changes = [tags, secure_boot_enabled, vtpm_enabled, admin_username, custom_data, os_disk[0].storage_account_type] }
}

resource "azurerm_disk_encryption_set" "linuxvm_disk_encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  name                      = "disk-encryption-linuxvm-${var.tre_id}-${var.tre_resource_id}"
  location                  = data.azurerm_resource_group.ws.location
  resource_group_name       = data.azurerm_resource_group.ws.name
  key_vault_key_id          = data.azurerm_key_vault_key.ws_encryption_key[0].versionless_id
  encryption_type           = "EncryptionAtRestWithPlatformAndCustomerKeys"
  auto_key_rotation_enabled = true

  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.ws_encryption_identity[0].id]
  }
}

data "template_cloudinit_config" "config" {
  gzip          = true
  base64_encode = true

  part {
    content_type = "text/x-shellscript"
    content      = data.template_file.get_apt_keys.rendered
  }

  part {
    content_type = "text/cloud-config"
    content      = data.template_file.apt_sources_config.rendered
  }

  part {
    content_type = "text/x-shellscript"
    content      = data.template_file.pypi_sources_config.rendered
  }

  part {
    content_type = "text/x-shellscript"
    content      = data.template_file.vm_config.rendered
  }
}

data "template_file" "vm_config" {
  template = file("${path.module}/vm_config.sh")
  vars = {
    INSTALL_UI            = local.selected_image.install_ui ? 1 : 0
    SHARED_STORAGE_ACCESS = tobool(var.shared_storage_access) ? 1 : 0
    STORAGE_ACCOUNT_NAME  = data.azurerm_storage_account.stg.name
    STORAGE_ACCOUNT_KEY   = data.azurerm_storage_account.stg.primary_access_key
    HTTP_ENDPOINT         = data.azurerm_storage_account.stg.primary_file_endpoint
    FILESHARE_NAME        = var.shared_storage_access ? var.shared_storage_name : ""
    NEXUS_PROXY_URL       = local.nexus_proxy_url
    CONDA_CONFIG          = local.selected_image.conda_config ? 1 : 0
    VM_USER               = local.admin_username
    APT_SKU               = replace(local.apt_sku, ".", "")
  }
}

resource "azurerm_key_vault_secret" "linuxvm_password" {
  name         = local.vm_password_secret_name
  value        = "${local.admin_username}\n${random_password.password.result}"
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_dev_test_global_vm_shutdown_schedule" "shutdown_schedule" {
  count = var.enable_shutdown_schedule ? 1 : 0

  location              = data.azurerm_resource_group.ws.location
  virtual_machine_id    = azurerm_linux_virtual_machine.linuxvm.id
  daily_recurrence_time = var.shutdown_time
  timezone              = var.shutdown_timezone
  enabled               = var.enable_shutdown_schedule
  notification_settings {
    enabled = false
  }
}
