data "azurerm_key_vault" "ws" {
  count               = var.local_auth_enabled ? 1 : 0
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

# Read keys after the account update. Its managed key can remain null in a plan.
data "azurerm_cognitive_account" "api_key" {
  count               = var.local_auth_enabled ? 1 : 0
  name                = azurerm_cognitive_account.ai_foundry.name
  resource_group_name = data.azurerm_resource_group.ws.name

  depends_on = [azurerm_cognitive_account.ai_foundry]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  count        = var.local_auth_enabled ? 1 : 0
  name         = "${azurerm_cognitive_account.ai_foundry.name}-access-key"
  value        = data.azurerm_cognitive_account.api_key[0].primary_access_key
  key_vault_id = data.azurerm_key_vault.ws[0].id
  tags         = local.workspace_service_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# Grant access to this secret without exposing other workspace secrets.
resource "azurerm_role_assignment" "api_key_reader" {
  for_each = var.local_auth_enabled ? azurerm_role_assignment.inference : {}

  scope                = azurerm_key_vault_secret.openai_api_key[0].resource_versionless_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value.principal_id
  principal_type       = "Group"
}
