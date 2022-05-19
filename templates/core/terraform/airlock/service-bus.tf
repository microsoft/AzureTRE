# Utilize the existing service bus - add new queue
data "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "sb-${var.tre_id}"
  resource_group_name = var.resource_group_name

}

resource "azurerm_servicebus_queue" "update_status_queue" {
  name         = "update_status"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "status_changed_queue" {
  name         = "status_changed"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "in_progress_import_blob_created_queue" {
  name         = "in_progress_import_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "rejected_import_blob_created_queue" {
  name         = "rejected_import_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "scan_result_queue" {
  name         = "scan_result_queue"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "accepted_import_blob_created_queue" {
  name         = "accepted_import_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "in_progress_export_blob_created_queue" {
  name         = "inprogress_export_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "rejected_export_blob_created_queue" {
  name         = "rejected_export_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

# Accepted export
resource "azurerm_servicebus_queue" "accepted_export_blob_created_queue" {
  name         = "accepted_export_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}



