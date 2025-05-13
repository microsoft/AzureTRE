
data "azurerm_key_vault_secret" "workspace_client_id" {
  name         = "workspace-client-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "external" "app_role_members" {
  program = ["bash", "${path.module}/get_app_role_members.sh"]

  query = {
    auth_client_id      = var.auth_client_id
    auth_client_secret  = var.auth_client_secret
    auth_tenant_id      = var.auth_tenant_id
    workspace_client_id = data.azurerm_key_vault_secret.workspace_client_id.value
    azure_environment   = var.azure_environment
  }
}

data "azurerm_role_definition" "azure_ml_data_scientist" {
  name = "AzureML Data Scientist"
}

resource "azurerm_role_assignment" "app_role_members_aml_data_scientist" {
  for_each           = (data.external.app_role_members.result.principals == "") ? [] : toset(split("\n", data.external.app_role_members.result.principals))
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.azure_ml_data_scientist.id
  principal_id       = each.value
}

resource "azurerm_role_assignment" "app_role_members_reader" {
  for_each           = (data.external.app_role_members.result.principals == "") ? [] : toset(split("\n", data.external.app_role_members.result.principals))
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.reader.id
  principal_id       = each.value
}

resource "azurerm_role_assignment" "app_role_members_storage_blob_data_contributor" {
  for_each           = (data.external.app_role_members.result.principals == "") ? [] : toset(split("\n", data.external.app_role_members.result.principals))
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_blob_data_contributor.id
  principal_id       = each.value
}

resource "azurerm_role_assignment" "app_role_members_storage_file_data_contributor" {
  for_each           = (data.external.app_role_members.result.principals == "") ? [] : toset(split("\n", data.external.app_role_members.result.principals))
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_file_data_contributor.id
  principal_id       = each.value
}
