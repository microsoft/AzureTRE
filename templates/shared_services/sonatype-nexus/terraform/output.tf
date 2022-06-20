output "nexus_fqdn" {
  value = azurerm_app_service.nexus.default_site_hostname
}

output "address_prefixes" {
  value = jsonencode(data.azurerm_subnet.web_app.address_prefixes)
}

output "nexus_allowed_fqdns_list" {
  value = jsonencode(local.nexus_allowed_fqdns_list)
}
