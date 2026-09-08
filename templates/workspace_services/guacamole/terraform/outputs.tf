output "authentication_callback_uri" {
  value = "https://${azurerm_linux_web_app.guacamole.default_hostname}/oauth2/callback"
}

output "web_apps_addresses" {
  value = jsonencode(data.azurerm_subnet.web_apps.address_prefixes)
}

output "admin_connection_uri" {
  value = "https://${azurerm_linux_web_app.guacamole.default_hostname}/guacamole"
}

output "aci_subnet_id" {
  value = azurerm_subnet.aci.id
}

output "aci_subnet_name" {
  value = azurerm_subnet.aci.name
}
