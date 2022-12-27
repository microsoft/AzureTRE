output "app_gateway_fqdn" {
  value = azurerm_public_ip.appgwpip.fqdn
}

output "app_gateway_name" {
  value = azurerm_application_gateway.agw.name
}

output "static_web_storage" {
  value = azurerm_storage_account.staticweb.name
}
