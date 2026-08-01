# The API needs permissions to stop/start VMs

# TODO: the assigned builtin role gives too wide permissions.
# https://github.com/microsoft/AzureTRE/issues/2389
resource "azurerm_role_assignment" "api_vm_contributor" {
  scope                = azurerm_resource_group.ws.id
  role_definition_name = "Virtual Machine Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
}

# Needed to include untagged resources in cost reporting #2933
resource "azurerm_role_assignment" "api_reader" {
  scope                = azurerm_resource_group.ws.id
  role_definition_name = "Reader"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
}

# The API needs to read secrets (e.g. VM credentials, connection strings) that
# resources store in the workspace Key Vault, so they can be surfaced to researchers.
resource "azurerm_role_assignment" "api_keyvault_secrets_user" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
}
