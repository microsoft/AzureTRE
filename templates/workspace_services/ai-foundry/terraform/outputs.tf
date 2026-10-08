output "ai_foundry_id" {
  value       = azurerm_cognitive_account.ai_foundry.id
  description = "Resource ID of the AI Foundry account."
}

output "ai_foundry_name" {
  value       = azurerm_cognitive_account.ai_foundry.name
  description = "Name of the AI Foundry account."
}

output "openai_endpoint" {
  value       = "https://${azurerm_cognitive_account.ai_foundry.custom_subdomain_name}.openai.azure.com"
  description = "OpenAI API endpoint. Use Microsoft Entra ID or an API key when key authentication is enabled."
}

output "openai_api_key_secret_id" {
  value       = var.local_auth_enabled ? azurerm_key_vault_secret.openai_api_key[0].versionless_id : ""
  description = "Key Vault secret URI for the API key. Empty when key authentication is disabled."
}

output "openai_model_deployment" {
  value       = azurerm_cognitive_deployment.openai.name
  description = "Deployment name to use in chat-completions requests."
}

output "workspace_address_spaces" {
  value       = data.azurerm_virtual_network.ws.address_space
  description = "Network address ranges of the workspace virtual network."
}
