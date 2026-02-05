## Subscriptions
resource "azurerm_eventgrid_event_subscription" "import_approved_blob_created" {
  name  = "import-approved-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_airlock_workspace.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.import_approved_blob_created,
    azurerm_role_assignment.servicebus_sender_import_approved_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_inprogress_blob_created" {
  name  = "export-inprogress-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_airlock_workspace.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.export_inprogress_blob_created,
    azurerm_role_assignment.servicebus_sender_export_inprogress_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_rejected_blob_created" {
  name  = "export-rejected-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_airlock_workspace.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.export_rejected_blob_created,
    azurerm_role_assignment.servicebus_sender_export_rejected_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_blocked_blob_created" {
  name  = "export-blocked-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_airlock_workspace.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.export_blocked_blob_created,
    azurerm_role_assignment.servicebus_sender_export_blocked_blob_created
  ]
}
