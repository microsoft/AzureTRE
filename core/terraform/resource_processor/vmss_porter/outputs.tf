output "principal_id" {
  description = "Principal ID of the resource processor managed identity."
  value       = azurerm_user_assigned_identity.vmss_msi.principal_id
}
