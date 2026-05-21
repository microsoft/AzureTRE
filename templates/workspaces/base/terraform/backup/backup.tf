
resource "azapi_resource" "vault" {
  type      = "Microsoft.RecoveryServices/vaults@2024-04-01"
  name      = local.vault_name
  parent_id = var.resource_group_id
  location  = var.location
  tags      = var.tre_workspace_tags

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  body = {
    properties = merge(
      {
        redundancySettings = {
          standardTierStorageRedundancy = "ZoneRedundant"
        }
      },
      var.enable_cmk_encryption ? {
        encryption = {
          infrastructureEncryption = "Enabled"
          kekIdentity = {
            userAssignedIdentity      = var.encryption_identity_id
            useSystemAssignedIdentity = false
          }
          keyVaultProperties = {
            keyUri = var.encryption_key_versionless_id
          }
        }
      } : {}
    )
    sku = {
      name = "Standard"
      tier = "Standard"
    }
  }

  lifecycle { ignore_changes = [body.properties.encryption, tags] }
}

resource "azurerm_backup_policy_vm" "vm_policy" {
  name                = local.vm_backup_policy_name
  resource_group_name = var.resource_group_name
  recovery_vault_name = azapi_resource.vault.name


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
    azapi_resource.vault
  ]


}

resource "azurerm_backup_policy_file_share" "file_share_policy" {
  name                = local.fs_backup_policy_name
  resource_group_name = var.resource_group_name
  recovery_vault_name = azapi_resource.vault.name

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
    azapi_resource.vault
  ]

}
