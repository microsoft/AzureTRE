output "identity_id" {
  value = azurerm_user_assigned_identity.id.id
}

output "managed_identity" {
  value = azurerm_user_assigned_identity.id
}
