
data "azurerm_data_factory" "adf_core" {
  name                = "adf-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

# Create a private endpoint to the storage account from the data platform
resource "azurerm_data_factory_managed_private_endpoint" "adf_dataplatform_pe" {
  name                = "pe-adf-ws-${local.workspace_resource_name_suffix}"
  data_factory_id     = data.azurerm_data_factory.adf_core.id
  target_resource_id  = azurerm_storage_account.stg.id
  subresource_name    = "file"
}

# Approve the private endpoint connection
resource "null_resource" "approve_private_endpoint" {
  triggers = {
    endpoint_id = azurerm_data_factory_managed_private_endpoint.adf_dataplatform_pe.id
  }
  provisioner "local-exec" {
    command = <<-EOT
      az login --service-principal -u "$ARM_CLIENT_ID" -p "$ARM_CLIENT_SECRET" --tenant "$ARM_TENANT_ID" &&
      az network private-endpoint-connection approve --id ${azurerm_data_factory_managed_private_endpoint.adf_dataplatform_pe.id} --resource-group ${azurerm_resource_group.ws.name}
    EOT
    environment = {
      ARM_CLIENT_ID       = var.arm_client_id
      ARM_CLIENT_SECRET   = var.arm_client_secret
      ARM_TENANT_ID       = var.arm_tenant_id
    }
  }
}

# Create a linked service in the data factory to the file storage
resource "azurerm_data_factory_linked_service_azure_file_storage" "ls_shared_file" {
  name                     = "ls-adf-shared_storage-${local.workspace_resource_name_suffix}"
  data_factory_id          = data.azurerm_data_factory.adf_core.id
  connection_string        = azurerm_storage_account.stg.primary_connection_string
  integration_runtime_name = "adf-ir-${var.tre_id}"
  file_share               = "vm-shared-storage"
}

# Create a data source in the data factory
