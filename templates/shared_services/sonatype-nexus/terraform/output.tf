output "nexus_fqdn" {
  value = azurerm_app_service.nexus.default_site_hostname
}