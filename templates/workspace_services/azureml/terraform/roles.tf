
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

# Legacy: Fallback to script-based role assignments if AAD groups are not available
data "azurerm_key_vault_secret" "workspace_client_id" {
  name         = "workspace-client-id"
  key_vault_id = data.azurerm_key_vault.ws.id
}

data "external" "app_role_members" {
  count   = (var.workspace_researchers_group_id == "" && var.workspace_owners_group_id == "") ? 1 : 0
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
  for_each           = (var.workspace_researchers_group_id == "" && var.workspace_owners_group_id == "" && length(data.external.app_role_members) > 0 && data.external.app_role_members[0].result.principals != "") ? toset(split("\n", data.external.app_role_members[0].result.principals)) : []
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.azure_ml_data_scientist.id
  principal_id       = each.value
}

resource "azurerm_role_assignment" "app_role_members_reader" {
  for_each           = (var.workspace_researchers_group_id == "" && var.workspace_owners_group_id == "" && length(data.external.app_role_members) > 0 && data.external.app_role_members[0].result.principals != "") ? toset(split("\n", data.external.app_role_members[0].result.principals)) : []
  scope              = azapi_resource.aml_workspace.output.id
  role_definition_id = data.azurerm_role_definition.reader.id
  principal_id       = each.value
}

resource "azurerm_role_assignment" "app_role_members_storage_blob_data_contributor" {
  for_each           = (var.workspace_researchers_group_id == "" && var.workspace_owners_group_id == "" && length(data.external.app_role_members) > 0 && data.external.app_role_members[0].result.principals != "") ? toset(split("\n", data.external.app_role_members[0].result.principals)) : []
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_blob_data_contributor.id
  principal_id       = each.value
}

resource "azurerm_role_assignment" "app_role_members_storage_file_data_contributor" {
  for_each           = (var.workspace_researchers_group_id == "" && var.workspace_owners_group_id == "" && length(data.external.app_role_members) > 0 && data.external.app_role_members[0].result.principals != "") ? toset(split("\n", data.external.app_role_members[0].result.principals)) : []
  scope              = azurerm_storage_account.aml.id
  role_definition_id = data.azurerm_role_definition.storage_file_data_contributor.id
  principal_id       = each.value
}
