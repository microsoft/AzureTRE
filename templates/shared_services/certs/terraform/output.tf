output "fqdn" {
  value = data.azurerm_public_ip.appgwpip_data.fqdn
}

output "application_gateway" {
  value = azurerm_application_gateway.agw.name
}

output "storage_account_name" {
  value = azurerm_storage_account.staticweb.name
}

output "storage_account_id" {
  value = azurerm_storage_account.staticweb.id
}

output "resource_group_name" {
  value = azurerm_application_gateway.agw.resource_group_name
}

output "keyvault" {
  value = data.azurerm_key_vault.key_vault.name
}

output "temp_certificate_name" {
  value = locals.certificate_name
}
