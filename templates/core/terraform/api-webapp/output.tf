output "api_fqdn" {
  value = azurerm_app_service.api.default_site_hostname
}
