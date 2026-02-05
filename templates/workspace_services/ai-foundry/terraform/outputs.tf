output "ai_foundry_id" {
  value       = azurerm_cognitive_account.ai_foundry.id
  description = "The resource ID of the AI Foundry account"
}

output "ai_foundry_name" {
  value       = azurerm_cognitive_account.ai_foundry.name
  description = "The name of the AI Foundry account"
}

output "connection_uri" {
  value       = "https://ai.azure.com/resource/overview?tid=${data.azurerm_client_config.current.tenant_id}&wsid=${azurerm_cognitive_account.ai_foundry.id}"
  description = "The connection URI for accessing the AI Foundry in Azure AI Foundry portal"
}

output "is_exposed_externally" {
  value       = var.is_exposed_externally
  description = "Whether the service is accessible from outside the workspace network"
}

output "workspace_address_spaces" {
  value       = data.azurerm_virtual_network.ws.address_space
  description = "The address spaces of the workspace virtual network"
}
