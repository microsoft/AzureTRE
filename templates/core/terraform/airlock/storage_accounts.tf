# 'External' storage account
resource "azurerm_storage_account" "sa_external_import" {
  name                     = local.airlock_external_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    description = "airlock;import;external"
  }

  lifecycle { ignore_changes = [tags] }
}

# 'In-Progress' storage account
resource "azurerm_storage_account" "sa_in-progress_import" {
  name                     = local.airlock_in_progress_import_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    description = "airlock;import;in-progress"
  }

  lifecycle { ignore_changes = [tags] }
}


# 'Rejected' storage account
resource "azurerm_storage_account" "sa_rejected_import" {
  name                     = local.airlock_rejected_import_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    description = "airlock;import;rejected"
  }

  lifecycle { ignore_changes = [tags] }
}
