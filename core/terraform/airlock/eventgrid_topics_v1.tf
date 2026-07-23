# Legacy (v1) EventGrid system topics and subscriptions for per-stage storage accounts
# These are only deployed when enable_legacy_airlock = true

resource "azurerm_eventgrid_system_topic" "import_inprogress_blob_created" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = local.import_inprogress_sys_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name
  source_resource_id  = azurerm_storage_account.sa_import_in_progress[0].id
  topic_type          = "Microsoft.Storage.StorageAccounts"

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "airlock;import-in-progress-sa"
  })

  depends_on = [
    azurerm_storage_account.sa_import_in_progress
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_import_inprogress_blob_created" {
  count                = var.enable_legacy_airlock ? 1 : 0
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.import_inprogress_blob_created[0].identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.import_inprogress_blob_created
  ]
}


resource "azurerm_eventgrid_system_topic" "import_rejected_blob_created" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = local.import_rejected_sys_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name
  source_resource_id  = azurerm_storage_account.sa_import_rejected[0].id
  topic_type          = "Microsoft.Storage.StorageAccounts"

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "airlock;import-rejected-sa"
  })

  depends_on = [
    azurerm_storage_account.sa_import_rejected,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_import_rejected_blob_created" {
  count                = var.enable_legacy_airlock ? 1 : 0
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.import_rejected_blob_created[0].identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.import_rejected_blob_created
  ]
}

resource "azurerm_eventgrid_system_topic" "import_blocked_blob_created" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = local.import_blocked_sys_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name
  source_resource_id  = azurerm_storage_account.sa_import_blocked[0].id
  topic_type          = "Microsoft.Storage.StorageAccounts"

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "airlock;import-blocked-sa"
  })

  depends_on = [
    azurerm_storage_account.sa_import_blocked,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_import_blocked_blob_created" {
  count                = var.enable_legacy_airlock ? 1 : 0
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.import_blocked_blob_created[0].identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.import_blocked_blob_created
  ]
}


resource "azurerm_eventgrid_system_topic" "export_approved_blob_created" {
  count               = var.enable_legacy_airlock ? 1 : 0
  name                = local.export_approved_sys_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name
  source_resource_id  = azurerm_storage_account.sa_export_approved[0].id
  topic_type          = "Microsoft.Storage.StorageAccounts"

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "airlock;export-approved-sa"
  })

  depends_on = [
    azurerm_storage_account.sa_export_approved,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_export_approved_blob_created" {
  count                = var.enable_legacy_airlock ? 1 : 0
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.export_approved_blob_created[0].identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.export_approved_blob_created
  ]
}

# Legacy EventGrid subscriptions for per-stage storage accounts
resource "azurerm_eventgrid_event_subscription" "import_inprogress_blob_created" {
  count = var.enable_legacy_airlock ? 1 : 0
  name  = local.import_inprogress_eventgrid_subscription_name
  scope = azurerm_storage_account.sa_import_in_progress[0].id

  service_bus_topic_endpoint_id = azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.import_inprogress_blob_created,
    azurerm_role_assignment.servicebus_sender_import_inprogress_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "import_rejected_blob_created" {
  count = var.enable_legacy_airlock ? 1 : 0
  name  = local.import_rejected_eventgrid_subscription_name
  scope = azurerm_storage_account.sa_import_rejected[0].id

  service_bus_topic_endpoint_id = azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.import_rejected_blob_created,
    azurerm_role_assignment.servicebus_sender_import_rejected_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "import_blocked_blob_created" {
  count = var.enable_legacy_airlock ? 1 : 0
  name  = local.import_blocked_eventgrid_subscription_name
  scope = azurerm_storage_account.sa_import_blocked[0].id

  service_bus_topic_endpoint_id = azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.import_blocked_blob_created,
    azurerm_role_assignment.servicebus_sender_import_blocked_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_approved_blob_created" {
  count = var.enable_legacy_airlock ? 1 : 0
  name  = local.export_approved_eventgrid_subscription_name
  scope = azurerm_storage_account.sa_export_approved[0].id

  service_bus_topic_endpoint_id = azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.export_approved_blob_created,
    azurerm_role_assignment.servicebus_sender_export_approved_blob_created
  ]
}
