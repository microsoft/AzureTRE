
# Role assignments for workspace researchers group
resource "azurerm_role_assignment" "researchers_aml_data_scientist" {
  count              = var.workspace_researchers_group_id != "" ? 1 : 0
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.azure_ml_data_scientist.id
  principal_id       = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_reader" {
  count              = var.workspace_researchers_group_id != "" ? 1 : 0
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.reader.id
  principal_id       = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_storage_blob_data_contributor" {
  count              = var.workspace_researchers_group_id != "" ? 1 : 0
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_blob_data_contributor.id
  principal_id       = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_storage_file_data_contributor" {
  count              = var.workspace_researchers_group_id != "" ? 1 : 0
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_file_data_contributor.id
  principal_id       = var.workspace_researchers_group_id
}

# Role assignments for workspace owners group
resource "azurerm_role_assignment" "owners_aml_data_scientist" {
  count              = var.workspace_owners_group_id != "" ? 1 : 0
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.azure_ml_data_scientist.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_reader" {
  count              = var.workspace_owners_group_id != "" ? 1 : 0
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.reader.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_storage_blob_data_contributor" {
  count              = var.workspace_owners_group_id != "" ? 1 : 0
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_blob_data_contributor.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_storage_file_data_contributor" {
  count              = var.workspace_owners_group_id != "" ? 1 : 0
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_file_data_contributor.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_azureml_compute_operator" {
  count              = var.workspace_owners_group_id != "" ? 1 : 0
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.azureml_compute_operator.id
  principal_id       = var.workspace_owners_group_id
}

data "azurerm_role_definition" "azure_ml_data_scientist" {
  name = "AzureML Data Scientist"
}
