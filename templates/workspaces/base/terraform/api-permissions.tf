# The API needs permissions to stop/start VMs

data "azurerm_user_assigned_identity" "api_id" {
  name                = "id-api-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}


# TODO: the assigned builtin role gives too wide permissions.
# https://github.com/microsoft/AzureTRE/issues/2389
resource "azurerm_role_assignment" "api_vm_contributor" {
  scope                = azurerm_resource_group.ws.id
  role_definition_name = "Virtual Machine Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id
}

resource "azuread_app_role_assignment" "workspace_airlock_managers_group" {
  count               = var.create_aad_groups ? 1 : 0
  app_role_id         = azuread_service_principal.workspace.app_role_ids["AirlockManager"]
  principal_object_id = azuread_group.workspace_airlock_managers[count.index].id
  resource_object_id  = azuread_service_principal.workspace.object_id
}
