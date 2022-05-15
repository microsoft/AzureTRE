data "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "airlock-sb-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
}


resource "azurerm_servicebus_queue" "accepted_import" {
  name         = "accepted_import_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "inprogress_export" {
  name         = "inprogress_export_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "rejected_export" {
  name         = "rejected_export_blob_created"
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}
