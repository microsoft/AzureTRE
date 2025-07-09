resource "azurerm_databricks_workspace" "databricks" {
  name                                  = local.databricks_workspace_name
  resource_group_name                   = data.azurerm_resource_group.ws.name
  location                              = data.azurerm_resource_group.ws.location
  sku                                   = "premium"
  managed_resource_group_name           = local.managed_resource_group_name
  infrastructure_encryption_enabled     = true
  public_network_access_enabled         = var.is_exposed_externally
  network_security_group_rules_required = "NoAzureDatabricksRules"
  tags                                  = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }

  custom_parameters {
    no_public_ip                                         = true
    public_subnet_name                                   = azurerm_subnet.host.name
    private_subnet_name                                  = azurerm_subnet.container.name
    virtual_network_id                                   = data.azurerm_virtual_network.ws.id
    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.host.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.container.id
    storage_account_name                                 = local.storage_name
  }

  depends_on = [
    azurerm_subnet_network_security_group_association.host,
    azurerm_subnet_network_security_group_association.container
  ]
}

resource "azurerm_databricks_access_connector" "this" {
  name                = "custom-unity-catalog-access-connector"
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  principal_id         = azurerm_databricks_access_connector.this.identity[0].principal_id # For system-assigned managed identity
  role_definition_name = "Storage Blob Data Contributor"
  scope                = data.azurerm_storage_account.shared.id  # Reference the existing storage account

  depends_on = [
    azurerm_databricks_workspace.databricks  # Ensure the Databricks workspace is created first
  ]
}

# resource "databricks_storage_credential" "managed_identity_credential" {
#   name                    = "${local.databricks_workspace_name}-managed-identity-credential"
#   provider                = databricks.workspace
#   azure_managed_identity {
#     access_connector_id  = azurerm_databricks_access_connector.this.id  # Reference the correct managed identity
#   }

#   depends_on = [
#     azurerm_databricks_workspace.databricks,
#     azurerm_databricks_access_connector.this,
#     azurerm_role_assignment.storage_blob_data_contributor
#   ]  # Ensure the workspace is created first
# }

# resource "databricks_external_location" "external_location_example" {
#   name                  = "${local.databricks_workspace_name}-external-location"
#   provider              = databricks.workspace
#   url                   = "abfss://datalake@${data.azurerm_storage_account.shared.name}.dfs.core.windows.net/"
#   # credential_name       = databricks_storage_credential.managed_identity_credential.id
#   credential_name       = "test-storage-credential"

#   depends_on = [azurerm_role_assignment.storage_blob_data_contributor]  # Ensure that the storage credential is created first
# }

