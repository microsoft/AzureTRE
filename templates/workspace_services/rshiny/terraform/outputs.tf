output "gitea_fqdn" {
  value = azurerm_linux_web_app.rshiny.default_hostname
}

output "authentication_callback_uri" {
  value = "https://${azurerm_linux_web_app.rshiny.default_hostname}/user/oauth2/oidc/callback"
}

output "connection_uri" {
  value = "https://${azurerm_linux_web_app.rshiny.default_hostname}/"
}

output "workspace_address_space" {
  value = jsonencode(data.azurerm_virtual_network.ws.address_space)
}

output "is_exposed_externally" {
  value = false
}
