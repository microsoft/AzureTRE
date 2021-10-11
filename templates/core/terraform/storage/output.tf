output "storage_account_name" {
  value = azurerm_storage_account.stg.name
}

output "storage_account_access_key" {
  value = azurerm_storage_account.stg.primary_access_key
}

output "storage_state_path" {
  value = azurerm_storage_share.storage_state_path.name
}
