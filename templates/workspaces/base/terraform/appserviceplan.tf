resource "azurerm_app_service_plan" "workspace" {
  count = var.deploy_app_service_plan ? 1 : 0

  name                = "plan-${var.tre_resource_id}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  kind                = "Linux"
  reserved            = "true"

  sku {
    tier = "PremiumV3"
    size = var.app_service_plan_sku
  }
}
