data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

data "azurerm_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

data "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = var.resource_group_name
}
