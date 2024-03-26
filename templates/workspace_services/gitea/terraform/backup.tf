data "azurerm_recovery_services_vault" "recovery_services_vault" {
  count               = local.enableBackup ? 1 : 0
  name                = local.rsv_name
  resource_group_name = azurerm_storage_account.gitea.resource_group_name
}

resource "azurerm_backup_policy_file_share" "vault_policy" {
  count               = local.enableBackup ? 1 : 0
  name                = local.rsv_policy_name
  resource_group_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].resource_group_name
  recovery_vault_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].name

  backup {
    frequency = "Daily"
    time      = "23:00"
  }

  retention_daily {
    count = 30
  }

  retention_weekly {
    count    = 4
    weekdays = ["Saturday"]
  }

  retention_monthly {
    count    = 2
    weekdays = ["Sunday"]
    weeks    = ["Last"]
  }
}

resource "azurerm_backup_container_storage_account" "gitea" {
  count               = local.enableBackup ? 1 : 0
  resource_group_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].resource_group_name
  recovery_vault_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].name
  storage_account_id  = azurerm_storage_account.gitea.id
}

resource "azurerm_backup_protected_file_share" "gitea" {
  count                     = local.enableBackup ? 1 : 0
  resource_group_name       = data.azurerm_recovery_services_vault.recovery_services_vault[0].resource_group_name
  recovery_vault_name       = data.azurerm_recovery_services_vault.recovery_services_vault[0].name
  source_storage_account_id = azurerm_backup_container_storage_account.gitea[0].storage_account_id
  source_file_share_name    = azurerm_storage_share.gitea.name
  backup_policy_id          = azurerm_backup_policy_file_share.vault_policy[0].id
}
