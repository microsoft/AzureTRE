# System topics
resource "azurerm_eventgrid_system_topic" "import_approved_blob_created" {
  name                   = local.import_approved_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_import_approved.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;approved-import-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_import_approved
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_eventgrid_system_topic" "export_inprogress_blob_created" {
  name                   = local.export_inprogress_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_export_inprogress.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;inprogress-export-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_export_inprogress
  ]

  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_eventgrid_system_topic" "export_rejected_blob_created" {
  name                   = local.export_rejected_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_export_rejected.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = {
    Publishers = "airlock;rejected-export-sa"
  }

  depends_on = [
    azurerm_storage_account.sa_export_rejected
  ]

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "sb-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_servicebus_queue" "import_approved_blob_created" {
  name                = local.import_approved_queue_name
  resource_group_name = local.core_resource_group_name
  namespace_name      = "sb-${var.tre_id}"
}

data "azurerm_servicebus_queue" "export_in_progress_blob_created" {
  name                = local.export_inprogress_queue_name
  resource_group_name = local.core_resource_group_name
  namespace_name      = "sb-${var.tre_id}"
}

data "azurerm_servicebus_queue" "export_rejected_blob_created" {
  name                = local.export_rejected_queue_name
  resource_group_name = local.core_resource_group_name
  namespace_name      = "sb-${var.tre_id}"
}

## Subscriptions
resource "azurerm_eventgrid_event_subscription" "import_approved_blob_created" {
  name  = "import-approved-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_import_approved.id

  service_bus_queue_endpoint_id = data.azurerm_servicebus_queue.import_approved_blob_created.id

  depends_on = [
    azurerm_eventgrid_system_topic.import_approved_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_inprogress_blob_created" {
  name  = "export-inprogress-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_export_inprogress.id

  service_bus_queue_endpoint_id = data.azurerm_servicebus_queue.export_in_progress_blob_created.id

  depends_on = [
    azurerm_eventgrid_system_topic.export_inprogress_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_rejected_blob_created" {
  name  = "export-rejected-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_export_rejected.id

  service_bus_queue_endpoint_id = data.azurerm_servicebus_queue.export_rejected_blob_created.id

  depends_on = [
    azurerm_eventgrid_system_topic.export_rejected_blob_created
  ]
}
