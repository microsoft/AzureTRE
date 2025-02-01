output "fqdn" {
  value = azurerm_public_ip.appgwpip.fqdn
}

output "application_gateway_name" {
  value = azurerm_application_gateway.agw.name
}

output "storage_account_name" {
  value = azurerm_storage_account.staticweb.name
}

output "resource_group_name" {
  value = azurerm_application_gateway.agw.resource_group_name
}

output "keyvault_name" {
  value = data.azurerm_key_vault.key_vault.name
}

output "password_name" {
  value = local.password_name
}
