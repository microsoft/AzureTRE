output "connection_uri" {
  value = "${local.webapp_access_prefix}/guacamole/"
}

output "authentication_callback_uri" {
  value = local.webapp_auth_callback_url
}

output "web_apps_addresses" {
  value = jsonencode(data.azurerm_subnet.web_apps.address_prefixes)
}

output "routing_fqdn" {
  value = var.is_exposed_externally ? azurerm_linux_web_app.guacamole.default_hostname : ""
}
