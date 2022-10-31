output "gitea_fqdn" {
  value = azurerm_linux_web_app.gitea.default_hostname
}

output "connection_uri" {
  value = "https://${azurerm_linux_web_app.gitea.default_hostname}/"
}
