resource "azurerm_data_factory" "adf_core" {
  name                            = "adf-${var.tre_id}"
  location                        = azurerm_resource_group.core.location
  resource_group_name             = azurerm_resource_group.core.name
  managed_virtual_network_enabled = true
}

resource "azurerm_data_factory_managed_private_endpoint" "adf_dataplatform_pe" {
  name                = "pe-adf-sadataplatform"
  data_factory_id     = azurerm_data_factory.adfcore.id
  target_resource_id  = data.azurerm_storage_account.sadataplatform.id
  subresource_name    = "blob"
}

# resource "azurerm_data_factory_integration_runtime_managed" "adf_ir" {
#   name            = "adf-ir-${var.tre_id}
#   data_factory_id = azurerm_data_factory.adf_core.id
#   location        = azurerm_resource_group.core.location
#   node
# }

