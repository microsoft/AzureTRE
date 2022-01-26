output "api_fqdn" {
  value = azurerm_app_service.api.default_site_hostname
}

output "core_app_service_plan_id" {
  value = azurerm_app_service_plan.core.id
}
