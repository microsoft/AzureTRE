output "gitea_fqdn" {
  value = azurerm_app_service.gitea.default_site_hostname
}

output "connection_uri" {
  value = "https://${azurerm_app_service.gitea.default_site_hostname}/"
}
