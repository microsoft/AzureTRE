
resource "azurerm_recovery_services_vault" "vault" {
  name                = local.vault_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"
  soft_delete_enabled = false
  storage_mode_type   = "ZoneRedundant" #  Possible values are "GeoRedundant", "LocallyRedundant" and "ZoneRedundant". Defaults to "GeoRedundant".
  tags                = var.tre_workspace_tags

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.encryption_identity[0].id]
    }
  }

  dynamic "encryption" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_id                            = azurerm_key_vault_key.encryption_key[0].versionless_id
      infrastructure_encryption_enabled = true
      user_assigned_identity_id         = azurerm_user_assigned_identity.encryption_identity[0].id
      use_system_assigned_identity      = false
    }
  }

  lifecycle { ignore_changes = [encryption, tags] }

}

resource "azurerm_backup_policy_vm" "vm_policy" {
  name                = local.vm_backup_policy_name
  resource_group_name = var.resource_group_name
  recovery_vault_name = azurerm_recovery_services_vault.vault.name


  timezone = "UTC"

  backup {
    frequency = "Daily"
    time      = "22:00"
  }

  retention_daily {
    count = 14
  }

  retention_weekly {
    count    = 4
    weekdays = ["Sunday"]
  }

  retention_monthly {
    count    = 12
    weekdays = ["Monday"]
    weeks    = ["First"]
  }

  retention_yearly {
    count    = 2
    months   = ["December"]
    weekdays = ["Sunday"]
    weeks    = ["Last"]
  }

  depends_on = [
    azurerm_recovery_services_vault.vault
  ]


}

resource "azurerm_backup_policy_file_share" "file_share_policy" {
  name                = local.fs_backup_policy_name
  resource_group_name = var.resource_group_name
  recovery_vault_name = azurerm_recovery_services_vault.vault.name

  timezone = "UTC"

  backup {
    frequency = "Daily"
    time      = "23:00"
  }

  retention_daily {
    count = 14
  }

  retention_weekly {
    count    = 4
    weekdays = ["Sunday"]
  }

  retention_monthly {
    count    = 12
    weekdays = ["Monday"]
    weeks    = ["First"]
  }

  retention_yearly {
    count    = 2
    months   = ["December"]
    weekdays = ["Sunday"]
    weeks    = ["Last"]
  }

  depends_on = [
    azurerm_recovery_services_vault.vault
  ]

}
