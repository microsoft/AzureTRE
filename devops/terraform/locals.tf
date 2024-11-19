locals {
  # The key store for encryption keys could either be external or created by terraform
  key_store_id = var.enable_cmk_encryption ? (var.external_key_store_id != null ? var.external_key_store_id : data.azurerm_key_vault.encryption_kv[0].id) : null
}
