output "vault_name" {
  value = azapi_resource.vault.name
}

output "vault_id" {
  value = azapi_resource.vault.id
}

output "vm_backup_policy_name" {
  value = azurerm_backup_policy_vm.vm_policy.name
}

output "vm_backup_policy_id" {
  value = azurerm_backup_policy_vm.vm_policy.id
}

output "fileshare_backup_policy_name" {
  value = azurerm_backup_policy_file_share.file_share_policy.name
}

output "fileshare_backup_policy_id" {
  value = azurerm_backup_policy_file_share.file_share_policy.id
}
