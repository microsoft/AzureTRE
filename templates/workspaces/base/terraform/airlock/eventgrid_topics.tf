# System topics
resource "azurerm_eventgrid_system_topic" "accepted_import_blob_created_system_topic" {
  name                   = local.egst_accepted_import_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_accepted_import.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;accepted-import-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_accepted_import
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_eventgrid_system_topic" "inprogress_export_blob_created_system_topic" {
  name                   = local.egst_inprogress_export_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_inprogress_export.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;inprogress-export-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_inprogress_export
  ]

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_eventgrid_system_topic" "rejected_export_blob_created_system_topic" {
  name                   = local.egst_rejected_export_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_rejected_export.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;rejected-export-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_rejected_export
  ]

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "sb-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_servicebus_queue" "accepted_import_blob_created_queue" {
  name                = "accepted_import_blob_created"
  resource_group_name = local.core_resource_group_name
  namespace_name      = "sb-${var.tre_id}"
}

data "azurerm_servicebus_queue" "in_progress_export_blob_created_queue" {
  name                = "inprogress_export_blob_created"
  resource_group_name = local.core_resource_group_name
  namespace_name      = "sb-${var.tre_id}"
}

data "azurerm_servicebus_queue" "rejected_export_blob_created_queue" {
  name                = "rejected_export_blob_created"
  resource_group_name = local.core_resource_group_name
  namespace_name      = "sb-${var.tre_id}"
}

## Subscriptions
resource "azurerm_eventgrid_event_subscription" "accepted-blob-created-subscription" {
  name  = "accepted-import-blob-created-${local.workspace_resource_name_suffix}"
  scope = azurerm_storage_account.sa_accepted_import.id

  service_bus_queue_endpoint_id = data.azurerm_servicebus_queue.accepted_import_blob_created_queue.id
}

resource "azurerm_eventgrid_event_subscription" "inprogress-export-blob-created-subscription" {
  name  = "inprogress-export-blob-created-${local.workspace_resource_name_suffix}"
  scope = azurerm_storage_account.sa_inprogress_export.id

  service_bus_queue_endpoint_id = data.azurerm_servicebus_queue.in_progress_export_blob_created_queue.id
}

resource "azurerm_eventgrid_event_subscription" "rejected-export-blob-created-subscription" {
  name  = "rejected-export-blob-created-${local.workspace_resource_name_suffix}"
  scope = azurerm_storage_account.sa_rejected_export.id

  service_bus_queue_endpoint_id = data.azurerm_servicebus_queue.rejected_export_blob_created_queue.id
}
