# Use a built-in inference role without granting model deployment or key retrieval.
# It includes more than chat completions. See the service documentation for the
# accepted permission boundary and why higher-privilege roles are excluded.
# https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-openai-user
resource "azurerm_role_assignment" "inference" {
  for_each = {
    owners      = var.workspace_owners_group_id
    researchers = var.workspace_researchers_group_id
  }

  scope                = azurerm_cognitive_account.ai_foundry.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = each.value
  principal_type       = "Group"

  # Do not validate these variables globally: that would also block cleanup
  # after a failed installation into a workspace without groups.
  lifecycle {
    precondition {
      condition     = length(trimspace(each.value)) > 0
      error_message = "AI Foundry requires a parent workspace with auth_type Automatic and create_aad_groups true."
    }
  }
}
