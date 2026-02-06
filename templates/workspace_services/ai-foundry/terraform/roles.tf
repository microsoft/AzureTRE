# Role definitions
data "azurerm_role_definition" "azure_ai_developer" {
  name = "Azure AI Developer"
}

data "azurerm_role_definition" "cognitive_services_user" {
  name = "Cognitive Services User"
}

data "azurerm_role_definition" "cognitive_services_contributor" {
  name = "Cognitive Services Contributor"
}

data "azurerm_role_definition" "reader" {
  name = "Reader"
}

data "azurerm_role_definition" "key_vault_secrets_user" {
  name = "Key Vault Secrets User"
}

# Note: Storage roles are managed by the base workspace template.
# AI Foundry creates its own Key Vault (separate from workspace key vault
# which contains sensitive infrastructure secrets like client_secret).
# Workspace group IDs are passed from the parent workspace properties.

# Role assignments for workspace owners group
resource "azurerm_role_assignment" "owners_ai_developer" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.azure_ai_developer.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_cognitive_services_user" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.cognitive_services_user.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_cognitive_services_contributor" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.cognitive_services_contributor.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "owners_reader" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.reader.id
  principal_id       = var.workspace_owners_group_id
}

# Role assignments for workspace researchers group
resource "azurerm_role_assignment" "researchers_ai_developer" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.azure_ai_developer.id
  principal_id       = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_cognitive_services_user" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.cognitive_services_user.id
  principal_id       = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_cognitive_services_contributor" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.cognitive_services_contributor.id
  principal_id       = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "researchers_reader" {
  scope              = azurerm_cognitive_account.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.reader.id
  principal_id       = var.workspace_researchers_group_id
}

# AI Foundry Key Vault role assignments
# Required for accessing secrets used by AI Foundry (separate from workspace key vault)
resource "azurerm_role_assignment" "owners_aif_keyvault" {
  scope              = azurerm_key_vault.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.key_vault_secrets_user.id
  principal_id       = var.workspace_owners_group_id
}

resource "azurerm_role_assignment" "researchers_aif_keyvault" {
  scope              = azurerm_key_vault.ai_foundry.id
  role_definition_id = data.azurerm_role_definition.key_vault_secrets_user.id
  principal_id       = var.workspace_researchers_group_id
}
