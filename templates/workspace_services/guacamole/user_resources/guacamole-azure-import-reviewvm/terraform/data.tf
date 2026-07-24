data "azurerm_resource_group" "core" {
  provider = azurerm.core
  name     = "rg-${var.tre_id}"
}

data "azurerm_public_ip" "app_gateway_ip" {
  provider            = azurerm.core
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}
