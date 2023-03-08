data "azurerm_client_config" "deployer" {}

data "azurerm_monitor_diagnostic_categories" "agw" {
  resource_id = azurerm_application_gateway.agw.id
  depends_on = [
    azurerm_application_gateway.agw
  ]
}
