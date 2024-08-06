output "connection_uri" {
  value = "https://${azurerm_linux_web_app.mlflow.default_hostname}"
}

output "is_exposed_externally" {
  value = false
}
