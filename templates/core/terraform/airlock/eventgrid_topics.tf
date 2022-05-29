# Event grid topics
resource "azurerm_eventgrid_topic" "update_status" {
  name                = local.update_status_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = {
    Publishers = "Airlock Orchestrator;"
  }
}

resource "azurerm_eventgrid_topic" "status_changed" {
  name                = local.status_changed_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = {
    Publishers = "TRE API;"
  }
}

# System topic
resource "azurerm_eventgrid_system_topic" "import_inprogress_blob_created" {
  name                   = local.import_inprogress_sys_topic_name
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_import_in_progress.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;import-in-progress-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_import_in_progress
  ]

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_eventgrid_system_topic" "import_rejected_blob_created" {
  name                   = local.import_rejected_sys_topic_name
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_import_rejected.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;import-rejected-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_import_rejected
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_eventgrid_system_topic" "export_approved_blob_created" {
  name                   = local.export_approved_sys_topic_name
  location               = var.location
  resource_group_name    = var.resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_export_approved.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;export-approved-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_export_approved
  ]

  lifecycle { ignore_changes = [tags] }
}


# Custom topic (for scanning)
resource "azurerm_eventgrid_topic" "scan_result" {
  name                = local.scan_result_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = {
    Publishers = "airlock;custom scanning service;"
  }

  lifecycle { ignore_changes = [tags] }
}

## Subscriptions

resource "azurerm_eventgrid_event_subscription" "updated_status" {
  name  = local.update_status_eventgrid_subscription_name
  scope = azurerm_eventgrid_topic.update_status.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.update_status.id
}

resource "azurerm_eventgrid_event_subscription" "status_changed" {
  name  = local.status_changed_eventgrid_subscription_name
  scope = azurerm_eventgrid_topic.status_changed.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.status_changed.id
}

resource "azurerm_eventgrid_event_subscription" "import_inprogress_blob_created" {
  name  = local.import_inprogress_eventgrid_subscription_name
  scope = azurerm_storage_account.sa_import_in_progress.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.import_in_progress_blob_created.id
}

resource "azurerm_eventgrid_event_subscription" "import_rejected_blob_created" {
  name  = local.import_rejected_eventgrid_subscription_name
  scope = azurerm_storage_account.sa_import_rejected.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.import_rejected_blob_created.id
}

resource "azurerm_eventgrid_event_subscription" "export_approved_blob_created" {
  name  = local.export_approved_eventgrid_subscription_name
  scope = azurerm_storage_account.sa_export_approved.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.export_approved_blob_created.id
}

