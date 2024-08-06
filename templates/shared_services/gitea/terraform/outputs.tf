output "gitea_fqdn" {
  value = azurerm_linux_web_app.gitea.default_hostname
}

output "address_prefixes" {
  value = jsonencode(data.azurerm_subnet.web_app.address_prefixes)
}

output "gitea_allowed_fqdns_list" {
  value = jsonencode(local.gitea_allowed_fqdns_list)
}

output "connection_uri" {
  value = "https://${azurerm_linux_web_app.gitea.default_hostname}"
}

output "is_exposed_externally" {
  value = false
}
