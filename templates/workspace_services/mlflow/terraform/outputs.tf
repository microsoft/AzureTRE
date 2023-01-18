output "internal_connection_uri" {
  value = "https://${azurerm_linux_web_app.mlflow.default_hostname}"
}
