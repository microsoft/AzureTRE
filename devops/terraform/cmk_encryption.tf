resource "azurerm_user_assigned_identity" "tre_mgmt_encryption" {
  count               = var.enable_cmk_encryption ? 1 : 0
  resource_group_name = azurerm_resource_group.mgmt.name
  location            = azurerm_resource_group.mgmt.location

  name = "id-tre-mgmt-encryption"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "kv_mgmt_encryption_key_user" {
  count                = var.enable_cmk_encryption ? 1 : 0
  scope                = local.key_store_id
  role_definition_name = "Key Vault Crypto Service Encryption User"
  principal_id         = azurerm_user_assigned_identity.tre_mgmt_encryption[0].principal_id
}

# Key used to encrypt management resources
resource "azurerm_key_vault_key" "tre_mgmt_encryption" {
  count = var.enable_cmk_encryption ? 1 : 0

  name         = var.kv_mgmt_encryption_key_name
  key_vault_id = local.key_store_id
  key_type     = "RSA"
  key_size     = 2048

  key_opts = [
    "decrypt",
    "encrypt",
    "unwrapKey",
    "wrapKey",
  ]

  depends_on = [
    azurerm_role_assignment.current_user_to_key_vault_crypto_officer
  ]
}
