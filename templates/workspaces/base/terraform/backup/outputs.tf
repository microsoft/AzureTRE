output "backup_vault_name" {
  value = azurerm_recovery_services_vault.vault.name
}

output "backup_vault_vm_backup_policy_name" {
  value = azurerm_backup_policy_vm.vm_policy.name
}

output "backup_vault_fileshare_backup_policy_name" {
  value = azurerm_backup_policy_file_share.file_share_policy.name
}
