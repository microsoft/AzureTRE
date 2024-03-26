resource "azurerm_data_factory" "adf" {
  name                = "adf-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  managed_virtual_network_enabled = true
}
