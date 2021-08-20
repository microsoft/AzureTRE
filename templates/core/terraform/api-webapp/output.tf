# output "app_service_plan_id" {
#   value = azurerm_app_service_plan.core.id
# }

output "management_api_fqdn" {
  value = azurerm_app_service.management_api.default_site_hostname
}
