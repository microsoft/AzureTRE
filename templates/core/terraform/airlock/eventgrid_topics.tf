# Event grid topics
resource "azurerm_eventgrid_topic" "egt_update_status_topic" {
  name                = local.egt_update_status_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = {
    Publishers = "Airlock Orchestrator;"
  }
}

resource "azurerm_eventgrid_topic" "egt_status_changed_topic" {
  name                = local.egt_status_changed_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = {
    Publishers = "TRE API;"
  }
}

# System topic
resource "azurerm_eventgrid_system_topic" "inprogress_import_system_topic" {
  name                   = local.egst_inprogress_import_sys_topic_name
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_in_progress_import.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;in-progress-import-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_in_progress_import
  ]

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_eventgrid_system_topic" "rejected_import_system_topic" {
  name                   = local.egst_rejected_import_sys_topic_name
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_rejected_import.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;rejected-import-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_rejected_import
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_eventgrid_system_topic" "accepted_export_system_topic" {
  name                   = local.egst_accepted_export_sys_topic_name
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_accepted_export.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;accepted-export-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_accepted_export
  ]

  lifecycle { ignore_changes = [tags] }
}


# Custom topic (for scanning)
resource "azurerm_eventgrid_topic" "scan_result_topic" {
  name                = local.egt_scan_result_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = {
    Publishers = "airlock;custom scanning service;"
  }

  lifecycle { ignore_changes = [tags] }
}

## Subscriptions

resource "azurerm_eventgrid_event_subscription" "updated-status-subscription" {
  name  = "update-status"
  scope = azurerm_eventgrid_topic.egt_update_status_topic.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.update_status_queue.id
}

resource "azurerm_eventgrid_event_subscription" "status-changed-subscription" {
  name  = "status-changed"
  scope = azurerm_eventgrid_topic.egt_status_changed_topic.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.status_changed_queue.id
}

resource "azurerm_eventgrid_event_subscription" "inprogress-import-blob-created-subscription" {
  name  = "in-prog-import-blob-created"
  scope = azurerm_storage_account.sa_in_progress_import.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.in_progress_import_blob_created_queue.id
}

resource "azurerm_eventgrid_event_subscription" "rejected-import-blob-created-subscription" {
  name  = "rejected-import-blob-created"
  scope = azurerm_storage_account.sa_rejected_import.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.rejected_import_blob_created_queue.id
}

resource "azurerm_eventgrid_event_subscription" "accepted-export-blob-created-subscription" {
  name  = "accepted-export-blob-created"
  scope = azurerm_storage_account.sa_accepted_export.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.accepted_export_blob_created_queue.id
}

