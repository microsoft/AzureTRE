resource "azurerm_user_assigned_identity" "encryption" {
  count               = var.enable_cmk_encryption ? 1 : 0
  resource_group_name = azurerm_resource_group.core.name
  location            = azurerm_resource_group.core.location
  tags                = local.tre_core_tags

  name = "id-encryption-${var.tre_id}"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "kv_encryption_key_user" {
  count                = var.enable_cmk_encryption ? 1 : 0
  scope                = data.azurerm_key_vault.mgmt_kv[0].id
  role_definition_name = "Key Vault Crypto Service Encryption User"
  principal_id         = azurerm_user_assigned_identity.encryption[0].principal_id
}