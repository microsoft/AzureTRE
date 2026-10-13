output "vault_name" {
  description = "Cache vault name, or an empty string when retention is disabled."
  value       = var.enabled ? azurerm_key_vault.cache[0].name : ""
}
