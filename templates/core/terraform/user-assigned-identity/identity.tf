data "azurerm_subscription" "current" {}

resource "azurerm_user_assigned_identity" "id" {
  resource_group_name = var.resource_group_name
  location            = var.location

  name = "id-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
}

resource "azurerm_role_assignment" "contributor" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.id.principal_id
}