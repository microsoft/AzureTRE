output "authentication_callback_uri" {
  value = local.webapp_auth_callback_url
}

output "routing_fqdn" {
  value = var.is_exposed_externally ? azurerm_linux_web_app.guacamole.default_hostname : ""
}

output "web_apps_addresses" {
  value = jsonencode(data.azurerm_subnet.web_apps.address_prefixes)
}

output "admin_connection_uri" {
  value = "${local.webapp_access_prefix}/guacamole/"
}
