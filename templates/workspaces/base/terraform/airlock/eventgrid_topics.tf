## Subscriptions
resource "azurerm_eventgrid_event_subscription" "airlock_workspace_blob_created" {
  name  = "airlock-blob-created-ws-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_airlock_workspace.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  included_event_types = ["Microsoft.Storage.BlobCreated"]

  depends_on = [
    azurerm_eventgrid_system_topic.airlock_workspace_blob_created,
    azurerm_role_assignment.servicebus_sender_airlock_workspace_blob_created
  ]
}
