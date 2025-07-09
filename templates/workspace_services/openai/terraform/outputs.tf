output "openai_fqdn" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_deployment_id" {
  value = azurerm_cognitive_deployment.openai.name
}

output "workspace_address_space" {
  value = jsonencode(data.azurerm_virtual_network.ws.address_space)
}
