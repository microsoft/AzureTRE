## Subscriptions
# Subscribe to blob created events on the global workspace storage account
# Events are filtered/routed by the airlock processor using container metadata (workspace_id, stage)
resource "azurerm_eventgrid_event_subscription" "airlock_workspace_blob_created" {
  name  = "airlock-blob-created-ws-${var.short_workspace_id}"
  scope = data.azurerm_storage_account.sa_airlock_workspace_global.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  included_event_types = ["Microsoft.Storage.BlobCreated"]

  # Filter to only events for containers belonging to this workspace
  advanced_filter {
    string_contains {
      key    = "subject"
      values = [var.short_workspace_id]
    }
  }

  depends_on = [
    data.azurerm_eventgrid_system_topic.airlock_workspace_global_blob_created
  ]
}
