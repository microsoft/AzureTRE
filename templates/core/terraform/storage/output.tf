output "storage_account_name" {
  value = azurerm_storage_account.stg.name
}

output "storage_account_access_key" {
  value = azurerm_storage_account.stg.primary_access_key
}

