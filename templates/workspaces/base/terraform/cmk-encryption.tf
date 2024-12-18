resource "azurerm_user_assigned_identity" "encryption_identity" {
  count               = var.enable_cmk_encryption ? 1 : 0
  resource_group_name = azurerm_resource_group.ws.name
  location            = azurerm_resource_group.ws.location
  tags                = local.tre_workspace_tags

  name = local.encryption_identity_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "kv_encryption_key_user" {
  count                = var.enable_cmk_encryption ? 1 : 0
  scope                = var.key_store_id
  role_definition_name = "Key Vault Crypto Service Encryption User"
  principal_id         = azurerm_user_assigned_identity.encryption_identity[0].principal_id
}

resource "azurerm_key_vault_key" "encryption_key" {
  count = var.enable_cmk_encryption ? 1 : 0

  name         = local.kv_encryption_key_name
  key_vault_id = var.key_store_id
  key_type     = "RSA"
  key_size     = 2048

  key_opts = [
    "decrypt",
    "encrypt",
    "unwrapKey",
    "wrapKey",
  ]

  depends_on = [
    azurerm_role_assignment.kv_encryption_key_user
  ]
}
