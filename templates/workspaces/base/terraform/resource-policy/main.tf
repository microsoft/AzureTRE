# The workspace owns this assignment. Removing a Foundry service must not remove it.
resource "azurerm_resource_group_policy_assignment" "blocked_resource_types" {
  count = length(var.blocked_resource_types) > 0 ? 1 : 0

  name                 = "tre-blocked-resource-types"
  display_name         = "Block selected Azure resource types in this TRE workspace"
  description          = "Deny creation and updates of selected resource types. Existing resources are not disabled."
  resource_group_id    = var.resource_group_id
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/6c112d4e-5bc7-47ae-a041-ea2d9dccd749"
  enforce              = true

  parameters = jsonencode({
    listOfResourceTypesNotAllowed = { value = sort(tolist(var.blocked_resource_types)) }
    effect                        = { value = "Deny" }
  })
}
