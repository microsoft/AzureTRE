output "azureml_workspace_name" {
    value = azurerm_machine_learning_workspace.ml.name
}

output "azureml_acr_id" {
    value = module.acr.id
}

output "azureml_storage_account_id" {
    value = module.storage.storage_account_id
}