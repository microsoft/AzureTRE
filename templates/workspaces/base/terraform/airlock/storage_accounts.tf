# 'Accepted' storage account
resource "azurerm_storage_account" "sa_accepted_import" {
  name                     = local.airlock_accepted_import_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    description = "airlock;import;accepted"
  }

  lifecycle { ignore_changes = [tags] }
}

# 'Drop' location for export
resource "azurerm_storage_account" "sa_internal_export" {
  name                     = local.airlock_internal_export_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    description = "airlock;export;internal"
  }

  lifecycle { ignore_changes = [tags] }
}

# 'In-progress' location for export
resource "azurerm_storage_account" "sa_inprogress_export" {
  name                     = local.airlock_inprogress_export_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    description = "airlock;export;inprogress"
  }

  lifecycle { ignore_changes = [tags] }
}

# 'Rejected' location for export
resource "azurerm_storage_account" "sa_rejected_export" {
  name                     = local.airlock_rejected_export_storage_name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "GRS"

  tags = {
    description = "airlock;export;rejected"
  }

  lifecycle { ignore_changes = [tags] }
}
