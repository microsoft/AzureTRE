data "azurerm_recovery_services_vault" "recovery_services_vault" {
  count               = local.enableBackup ? 1 : 0
  name                = local.rsv_name
  resource_group_name = azurerm_storage_account.gitea.resource_group_name
}

# This code is executed on destroy-time before endpoints are removed.
resource "terraform_data" "delete_storage_account_lock" {
  input = {
    storage_account_id = azurerm_storage_account.gitea.id
  }
  provisioner "local-exec" {
    when       = destroy
    on_failure = continue
    command    = <<EOT
      az login --identity &&
      az lock delete \
        --ids ${self.input.storage_account_id}/providers/Microsoft.Authorization/locks/AzureBackupProtectionLock
    EOT
  }

  depends_on = [
    azurerm_private_endpoint.stgfilepe,
    azurerm_storage_account.gitea
  ]
}

resource "time_sleep" "wait_30_seconds_point_e" {
  count            = local.enableBackup ? 1 : 0
  create_duration  = "30s"
  destroy_duration = "120s"

  depends_on = [terraform_data.delete_storage_account_lock]
}

resource "terraform_data" "enable_soft_delete" {
  count = local.enableBackup ? 1 : 0

  input = {
    client_id           = data.azurerm_client_config.current.client_id
    subscription_id     = data.azurerm_client_config.current.subscription_id
    resource_group_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].resource_group_name
    rsv_name            = data.azurerm_recovery_services_vault.recovery_services_vault[0].name
  }

  provisioner "local-exec" {
    when       = destroy
    on_failure = continue
    command    = <<EOT
      az login --identity  -u ${self.input.client_id}
      sleep 30
      echo "Enable Soft Delete"
      az backup vault backup-properties set \
        --subscription ${self.input.subscription_id} \
        --resource-group ${self.input.resource_group_name} \
        --name ${self.input.rsv_name} \
        --soft-delete-feature-state Enable \
        --hybrid-backup-security-features Enable
      sleep 30
    EOT
  }

  depends_on = [time_sleep.wait_30_seconds_point_e]
}

resource "time_sleep" "wait_30_seconds_point_d" {
  count            = local.enableBackup ? 1 : 0
  create_duration  = "30s"
  destroy_duration = "120s"

  depends_on = [terraform_data.enable_soft_delete]
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

  depends_on = [time_sleep.wait_30_seconds_point_d]
}

resource "time_sleep" "wait_30_seconds_point_c" {
  count            = local.enableBackup ? 1 : 0
  create_duration  = "30s"
  destroy_duration = "120s"

  depends_on = [azurerm_backup_policy_file_share.vault_policy]
}

resource "azurerm_backup_container_storage_account" "gitea" {
  count               = local.enableBackup ? 1 : 0
  resource_group_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].resource_group_name
  recovery_vault_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].name
  storage_account_id  = azurerm_storage_account.gitea.id

  depends_on = [time_sleep.wait_30_seconds_point_c]
}

resource "time_sleep" "wait_30_seconds_point_b" {
  count            = local.enableBackup ? 1 : 0
  create_duration  = "30s"
  destroy_duration = "120s"

  depends_on = [azurerm_backup_container_storage_account.gitea]
}

resource "azurerm_backup_protected_file_share" "gitea" {
  count                     = local.enableBackup ? 1 : 0
  resource_group_name       = data.azurerm_recovery_services_vault.recovery_services_vault[0].resource_group_name
  recovery_vault_name       = data.azurerm_recovery_services_vault.recovery_services_vault[0].name
  source_storage_account_id = azurerm_backup_container_storage_account.gitea[0].storage_account_id
  source_file_share_name    = azurerm_storage_share.gitea.name
  backup_policy_id          = azurerm_backup_policy_file_share.vault_policy[0].id

  depends_on = [
    azurerm_backup_policy_file_share.vault_policy,
    time_sleep.wait_30_seconds_point_b
  ]
}

resource "time_sleep" "wait_30_seconds_point_a" {
  count            = local.enableBackup ? 1 : 0
  create_duration  = "30s"
  destroy_duration = "120s"

  depends_on = [azurerm_backup_protected_file_share.gitea]
}

resource "terraform_data" "disable_soft_delete" {
  count = local.enableBackup ? 1 : 0

  input = {
    client_id           = data.azurerm_client_config.current.client_id
    subscription_id     = data.azurerm_client_config.current.subscription_id
    resource_group_name = data.azurerm_recovery_services_vault.recovery_services_vault[0].resource_group_name
    rsv_name            = data.azurerm_recovery_services_vault.recovery_services_vault[0].name
  }

  provisioner "local-exec" {
    when       = destroy
    on_failure = continue
    command    = <<EOT
      az login --identity  -u ${self.input.client_id}
      sleep 30
      echo "Disable Soft Delete"
      az backup vault backup-properties set \
        --subscription ${self.input.subscription_id} \
        --resource-group ${self.input.resource_group_name} \
        --name ${self.input.rsv_name} \
        --soft-delete-feature-state Disable \
        --hybrid-backup-security-features Disable
      sleep 30
    EOT
  }

  depends_on = [time_sleep.wait_30_seconds_point_a]
}
