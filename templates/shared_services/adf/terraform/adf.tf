# This script is to create the adf that is used for the data transfer
# The private endpoint will need approving from the storage account
# Create the data factory
data "azurerm_resource_group" "rg" {
  name = local.core_resource_group_name
}

resource "azurerm_data_factory" "adf_core" {
  name                            = "adf-${var.tre_id}"
  location                        = data.azurerm_resource_group.rg.location
  resource_group_name             = data.azurerm_resource_group.rg.name
  managed_virtual_network_enabled = true
  tags                            = local.tre_shared_service_tags
}

# Create a managed integration runtime
resource "azurerm_data_factory_integration_runtime_azure" "adf_ir" {
  name                    = "adf-ir-${var.tre_id}"
  data_factory_id         = azurerm_data_factory.adf_core.id
  location                = data.azurerm_resource_group.rg.location
  virtual_network_enabled = true
}


