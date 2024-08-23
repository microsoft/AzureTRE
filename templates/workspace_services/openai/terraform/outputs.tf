output "openai_fqdn" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_deployment_id" {
  value = azurerm_cognitive_deployment.openai.name
}
