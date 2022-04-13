# See https://microsoft.github.io/AzureTRE/tre-developers/letsencrypt/
resource "azurerm_storage_account" "staticweb" {
  name                      = local.staticweb_storage_name
  resource_group_name       = data.azurerm_resource_group.rg.name
  location                  = data.azurerm_resource_group.rg.location
  account_kind              = "StorageV2"
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  enable_https_traffic_only = true
  allow_blob_public_access  = true

  tags = {
    tre_id = var.tre_id
  }

  static_website {
    index_document     = "index.html"
    error_404_document = "404.html"
  }

  lifecycle { ignore_changes = [tags] }
}
