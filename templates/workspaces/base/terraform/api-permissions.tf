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


