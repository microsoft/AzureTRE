output "fqdn" {
  value = azurerm_public_ip.appgwpip.fqdn
}

output "application_gateway_name" {
  value = azurerm_application_gateway.agw.name
}

output "storage_account_name" {
  value = azurerm_storage_account.staticweb.name
}

output "resource_group_name" {
  value = azurerm_application_gateway.agw.resource_group_name
}

output "keyvault_name" {
  value = data.azurerm_key_vault.key_vault.name
}

output "password_name" {
  value = local.password_name
}

output "auto_renewal_enabled" {
  description = "Whether auto-renewal is enabled for this certificate"
  value       = var.enable_auto_renewal
}

output "auto_renewal_logic_app_name" {
  description = "Name of the Logic App used for auto-renewal"
  value       = var.enable_auto_renewal ? azurerm_logic_app_workflow.cert_renewal[0].name : null
}

output "renewal_threshold_days" {
  description = "Number of days before expiry to trigger renewal"
  value       = var.renewal_threshold_days
}
