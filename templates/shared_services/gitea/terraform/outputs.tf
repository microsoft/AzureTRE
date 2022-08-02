output "gitea_fqdn" {
  value = azurerm_app_service.gitea.default_site_hostname
}

output "address_prefixes" {
  value = jsonencode(data.azurerm_subnet.web_app.address_prefixes)
}

output "gitea_allowed_fqdns_list" {
  value = jsonencode(local.gitea_allowed_fqdns_list)
}
