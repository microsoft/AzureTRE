output "airlock_notifier_logic_app_name" {
  value = azurerm_logic_app_standard.logic-app.name
}

output "airlock_notifier_logic_app_resource_group_name" {
  value = azurerm_logic_app_standard.logic-app.resource_group_name
}
