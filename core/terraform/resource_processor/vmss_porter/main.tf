terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.27.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.7.2"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.5.2"
    }
    template = {
      source  = "hashicorp/template"
      version = ">= 2.2.0"
    }
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

resource "azurerm_key_vault_secret" "resource_processor_vmss_password" {
  name         = "resource-processor-vmss-password"
  value        = random_password.password.result
  key_vault_id = var.key_vault_id
  tags         = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_user_assigned_identity" "vmss_msi" {
  name                = "id-vmss-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_disk_encryption_set" "vmss_disk_encryption" {
  count                     = var.enable_cmk_encryption ? 1 : 0
  name                      = "vmss-disk-encryption-rp-porter-${var.tre_id}"
  location                  = var.location
  resource_group_name       = var.resource_group_name
  key_vault_key_id          = data.azurerm_key_vault_key.tre_encryption[0].versionless_id
  encryption_type           = "EncryptionAtRestWithPlatformAndCustomerKeys"
  auto_key_rotation_enabled = true

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.vmss_msi.id]
  }

  depends_on = [
    azurerm_role_assignment.vmss_kv_encryption_key_user
  ]
}

resource "azurerm_linux_virtual_machine_scale_set" "vm_linux" {
  name                            = "vmss-rp-porter-${var.tre_id}"
  location                        = var.location
  resource_group_name             = var.resource_group_name
  sku                             = var.resource_processor_vmss_sku
  instances                       = 1
  admin_username                  = "adminuser"
  disable_password_authentication = false
  admin_password                  = random_password.password.result
  custom_data                     = data.template_cloudinit_config.config.rendered
  encryption_at_host_enabled      = true
  upgrade_mode                    = "Automatic"
  tags                            = local.tre_core_tags
  secure_boot_enabled             = true
  vtpm_enabled                    = true

  extension {
    auto_upgrade_minor_version = true
    automatic_upgrade_enabled  = false
    name                       = "healthRepairExtension"
    provision_after_extensions = []
    publisher                  = "Microsoft.ManagedServices"
    type                       = "ApplicationHealthLinux"
    type_handler_version       = "1.0"

    settings = jsonencode(
      {
        port        = 8080
        protocol    = "http"
        requestPath = "/health"
      }
    )
  }

  automatic_os_upgrade_policy {
    disable_automatic_rollback  = false
    enable_automatic_os_upgrade = true
  }

  rolling_upgrade_policy {
    max_batch_instance_percent              = 100
    max_unhealthy_instance_percent          = 100
    max_unhealthy_upgraded_instance_percent = 100
    pause_time_between_batches              = "PT1M"

  }

  automatic_instance_repair {
    enabled      = true
    grace_period = "PT10M"
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.vmss_msi.id]
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  os_disk {
    storage_account_type   = "Standard_LRS"
    caching                = "ReadWrite"
    disk_size_gb           = 64
    disk_encryption_set_id = var.enable_cmk_encryption ? azurerm_disk_encryption_set.vmss_disk_encryption[0].id : null
  }

  network_interface {
    name    = "nic1"
    primary = true

    ip_configuration {
      name      = "internal"
      primary   = true
      subnet_id = var.resource_processor_subnet_id
    }
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# CustomData (e.g. image tag to run) changes will only take affect after vmss instances are reimaged.
# https://docs.microsoft.com/en-us/azure/virtual-machines/custom-data#can-i-update-custom-data-after-the-vm-has-been-created
resource "terraform_data" "vm_linux_reimage" {
  provisioner "local-exec" {
    command = "az vmss reimage --name ${azurerm_linux_virtual_machine_scale_set.vm_linux.name} --resource-group ${var.resource_group_name}"
  }

  triggers_replace = [
    # although we mainly want to catch image tag changes, this covers any custom data change.
    azurerm_linux_virtual_machine_scale_set.vm_linux.custom_data
  ]

  depends_on = [
    azurerm_linux_virtual_machine_scale_set.vm_linux
  ]
}

resource "azurerm_role_assignment" "mgmt_storage_account_blob_contributor" {
  scope                = var.mgmt_storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "vmss_acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "vmss_sb_sender" {
  scope                = var.service_bus_namespace_id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "vmss_sb_receiver" {
  scope                = var.service_bus_namespace_id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "subscription_administrator" {
  # Below is a workaround TF replacing this resource when using the data object.
  scope                = var.subscription_id != "" ? "/subscriptions/${var.subscription_id}" : data.azurerm_subscription.current.id
  role_definition_name = "User Access Administrator"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "subscription_contributor" {
  # Below is a workaround TF replacing this resource when using the data object.
  scope                = var.subscription_id != "" ? "/subscriptions/${var.subscription_id}" : data.azurerm_subscription.current.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_role_assignment" "keyvault_vmss_role" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Administrator"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id // id-vmss-<TRE_ID>
}

resource "azurerm_role_assignment" "vmss_kv_encryption_key_user" {
  count                = var.enable_cmk_encryption ? 1 : 0
  scope                = var.key_store_id
  role_definition_name = "Key Vault Crypto Officer"
  principal_id         = azurerm_user_assigned_identity.vmss_msi.principal_id
}

resource "azurerm_private_endpoint" "mgmtblobpe" {
  name                = "pe-mgmt-blob-${var.tre_id}"
  location            = var.location
  resource_group_name = var.mgmt_resource_group_name
  subnet_id           = var.resource_processor_subnet_id
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-blobcore"
    private_dns_zone_ids = [var.blob_core_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-mgmt-${var.tre_id}"
    private_connection_resource_id = var.mgmt_storage_account_id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.2.0"
  arm_environment = var.arm_environment
}
