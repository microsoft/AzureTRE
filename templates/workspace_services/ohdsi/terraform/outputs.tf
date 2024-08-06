output "connection_uri" {
  value       = local.atlas_ui_url
  description = "Atlas Endpoint"

  precondition {
    condition     = local.atlas_ui_fqdn == azurerm_linux_web_app.atlas_ui.default_hostname
    error_message = "Computed FQDN is different than actual one."
  }
}

output "webapi_uri" {
  value       = local.ohdsi_webapi_url
  description = "WebAPI Endpoint"

  precondition {
    condition     = local.ohdsi_webapi_fqdn == azurerm_linux_web_app.ohdsi_webapi.default_hostname
    error_message = "Computed FQDN is different than actual one."
  }
}

output "authentication_callback_uri" {
  value = "${local.ohdsi_webapi_url_auth_callback}?client_name=OidcClient"
}

output "is_exposed_externally" {
  value = false
}
