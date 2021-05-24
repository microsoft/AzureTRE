data "azurerm_client_config" "deployer" {}

resource "azurerm_storage_account" "staticweb" {
    name = local.staticweb_storage_name
    resource_group_name = var.resource_group_name
    location = var.location
    account_kind = "StorageV2"
    access_tier = "Standard"
    account_replication_type = "LRS"
    enable_https_traffic_only = true
    allow_blob_public_access = false
    static_website {
      index_document = "index.html"
      error_404_document = "404.html"
    }
    tags = {
        environment = var.environment
    }
}

# Assign the identity deploying data contibutor rights.
# Needed to upload content to static web.
resource "azurerm_role_assignment" "stgwriter" {
  scope                = azurerm_storage_account.staticweb.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.deployer.object_id
}