output "internals" {
  value = jsonencode({
    authentication_callback_uri = local.webapp_auth_callback_url
    routing_fqdn                = var.is_exposed_externally ? azurerm_linux_web_app.guacamole.default_hostname : ""
    web_apps_addresses          = data.azurerm_subnet.web_apps.address_prefixes
  })
}

output "admin_connection_uri" {
  value = "${local.webapp_access_prefix}/guacamole/"
}
