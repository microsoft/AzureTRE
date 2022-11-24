output "internal_connection_uri" {
  value = "https://${azurerm_app_service.mlflow.default_site_hostname}"
}
