resource "azurerm_key_vault_access_policy" "app_gw_managed_identity" {
  key_vault_id = var.keyvault_id
  tenant_id    = azurerm_user_assigned_identity.agw_id.tenant_id
  object_id    = azurerm_user_assigned_identity.agw_id.principal_id

  key_permissions = [
    "Get",
  ]

  secret_permissions = [
    "Get",
  ]
}

data "azurerm_key_vault_certificate" "tlscert" {
  name         = var.certificate_name
  key_vault_id = var.keyvault_id
}
