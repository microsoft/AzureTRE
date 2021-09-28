output "azureml_workspace_name" {
  value = azurerm_machine_learning_workspace.ml.name
}

output "azureml_acr_id" {
  value = azurerm_container_registry.acr.id
}

output "azureml_storage_account_id" {
  value = data.azurerm_storage_account.ws.id
}