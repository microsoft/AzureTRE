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

resource "random_string" "username" {
  length      = 4
  upper       = true
  lower       = true
  numeric     = true
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
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_windows_virtual_machine" "windowsvm" {
  name                       = local.vm_name
  location                   = data.azurerm_resource_group.ws.location
  resource_group_name        = data.azurerm_resource_group.ws.name
  network_interface_ids      = [azurerm_network_interface.internal.id]
  size                       = local.vm_sizes[var.vm_size]
  allow_extension_operations = true
  admin_username             = random_string.username.result
  admin_password             = random_password.password.result
  encryption_at_host_enabled = true
  secure_boot_enabled        = local.secure_boot_enabled
  vtpm_enabled               = local.vtpm_enabled

  custom_data = base64encode(data.template_file.download_review_data_script.rendered)

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
    storage_account_type   = "Standard_LRS"
    disk_encryption_set_id = var.enable_cmk_encryption ? azurerm_disk_encryption_set.windowsvm_disk_encryption[0].id : null
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tre_user_resources_tags

  # ignore changes to secure_boot_enabled and vtpm_enabled as these are destructive
  # (may be allowed once https://github.com/hashicorp/terraform-provider-azurerm/issues/25808 is fixed)
  #
  lifecycle { ignore_changes = [tags, secure_boot_enabled, vtpm_enabled] }
}

resource "azurerm_disk_encryption_set" "windowsvm_disk_encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  name                      = "disk-encryption-windowsvm-${var.tre_id}-${var.tre_resource_id}"
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

resource "azurerm_virtual_machine_extension" "config_script" {
  name                 = "${azurerm_windows_virtual_machine.windowsvm.name}-vmextension"
  virtual_machine_id   = azurerm_windows_virtual_machine.windowsvm.id
  publisher            = "Microsoft.Compute"
  type                 = "CustomScriptExtension"
  type_handler_version = "1.10"
  tags                 = local.tre_user_resources_tags

  protected_settings = <<PROT
    {
      "commandToExecute": "powershell -ExecutionPolicy Unrestricted -NoProfile -NonInteractive -command \"cp c:/azuredata/customdata.bin c:/azuredata/configure.ps1; c:/azuredata/configure.ps1 \""
    }
PROT

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "windowsvm_password" {
  name         = "${local.vm_name}-admin-credentials"
  value        = "${random_string.username.result}\n${random_password.password.result}"
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

data "template_file" "download_review_data_script" {
  template = file("${path.module}/download_review_data.ps1")
  vars = {
    airlock_request_sas_url = var.airlock_request_sas_url
  }
}

