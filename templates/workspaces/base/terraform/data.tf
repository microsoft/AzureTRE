data "azurerm_client_config" "core" {
  provider = azurerm.core
}

data "azurerm_user_assigned_identity" "api_id" {
  provider            = azurerm.core
  name                = "id-api-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_user_assigned_identity" "resource_processor_vmss_id" {
  provider            = azurerm.core
  name                = "id-vmss-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_client_config" "current" {}
