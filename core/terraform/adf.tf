# This script is to create the adf that is used for the data transfer
# The private endpoint will need approving from the storage account
# Create the data factory
resource "azurerm_data_factory" "adf_core" {
  name                            = "adf-${var.tre_id}"
  location                        = azurerm_resource_group.core.location
  resource_group_name             = azurerm_resource_group.core.name
  managed_virtual_network_enabled = true
  tags                            = local.tre_core_tags
}

# Create a managed integration runtime
resource "azurerm_data_factory_integration_runtime_azure" "adf_ir" {
  name                    = "adf-ir-${var.tre_id}"
  data_factory_id         = azurerm_data_factory.adf_core.id
  location                = azurerm_resource_group.core.location
  virtual_network_enabled = true
}

# Create a private endpoint to the storage account from the data platform
# Will need to make this dynamic / comment out in future pushes so that it works in different environments
resource "azurerm_data_factory_managed_private_endpoint" "adf_dataplatform_pe" {
  name                = "pe-adf-sadataplatform"
  data_factory_id     = azurerm_data_factory.adf_core.id
  target_resource_id  = data.azurerm_storage_account.sadataplatform.id
  subresource_name    = "blob"
}

# TODO - could potentially create a linked service here
# resource "azurerm_data_factory_linked_service_azure_blob_storage" "adf_ls_dataplatform" {
#   name            = "adf-ls-${var.tre_id}"
#   data_factory_id = azurerm_
# }
