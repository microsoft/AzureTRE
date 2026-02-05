# TODO: Check what RBAC is needed by Researchers
resource "azurerm_role_assignment" "researchers_databricks_contributor" {
  count                = var.workspace_researchers_group_id != "" ? 1 : 0
  scope                = azurerm_databricks_workspace.databricks.id
  role_definition_name = "Contributor"
  principal_id         = var.workspace_researchers_group_id
}

resource "azurerm_role_assignment" "owners_databricks_contributor" {
  count                = var.workspace_owners_group_id != "" ? 1 : 0
  scope                = azurerm_databricks_workspace.databricks.id
  role_definition_name = "Contributor"
  principal_id         = var.workspace_owners_group_id
}
