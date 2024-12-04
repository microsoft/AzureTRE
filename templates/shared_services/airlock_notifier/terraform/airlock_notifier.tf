resource "azurerm_service_plan" "notifier_plan" {
  name                = "airlock-notifier-plan-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
  location            = data.azurerm_resource_group.core.location
  os_type             = "Windows"
  sku_name            = "WS1"

  tags = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_servicebus_queue" "notifications_queue" {
  name         = "notifications"
  namespace_id = data.azurerm_servicebus_namespace.core.id

  partitioning_enabled = false
}

/* The notification queue needs to be subscribed to the notification event-grid */
resource "azurerm_eventgrid_event_subscription" "airlock_notification" {
  name  = local.airlock_notification_eventgrid_subscription_name
  scope = data.azurerm_eventgrid_topic.airlock_notification.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.notifications_queue.id

  delivery_identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "servicebus_logic_app" {
  scope                = data.azurerm_servicebus_namespace.core.id
  role_definition_name = "Azure Service Bus Data Owner"
  principal_id         = azurerm_logic_app_standard.logic_app.identity[0].principal_id
}

resource "azurerm_logic_app_standard" "logic_app" {
  name                       = "airlock-notifier-app-${var.tre_id}"
  location                   = data.azurerm_resource_group.core.location
  resource_group_name        = data.azurerm_resource_group.core.name
  app_service_plan_id        = azurerm_service_plan.notifier_plan.id
  storage_account_name       = data.azurerm_storage_account.storage.name
  storage_account_access_key = data.azurerm_storage_account.storage.primary_access_key
  virtual_network_subnet_id  = data.azurerm_subnet.airlock_notification.id
  version                    = "~4"
  bundle_version             = "[1.*, 2.0.0)"
  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "node"
    "WEBSITE_NODE_DEFAULT_VERSION"          = "~20"
    "serviceBus_connectionString"           = data.azurerm_servicebus_namespace.core.default_primary_connection_string
    "serviceBus_fullyQualifiedNamespace"    = data.azurerm_servicebus_namespace.core.endpoint
    "serviceBus_queueName"                  = azurerm_servicebus_queue.notifications_queue.name
    "subscription"                          = data.azurerm_subscription.current.subscription_id
    "location"                              = data.azurerm_resource_group.core.location
    "resource_group"                        = data.azurerm_resource_group.core.name
    "smtp_server_address"                   = var.smtp_server_address
    "smtp_server_port"                      = var.smtp_server_port
    "smtp_server_enable_ssl"                = var.smtp_server_enable_ssl
    "smtp_username"                         = var.smtp_username
    "smtp_password"                         = var.smtp_password
    "smtp_from_email"                       = var.smtp_from_email
    "tre_url"                               = var.tre_url != "" ? var.tre_url : local.default_tre_url
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = data.azurerm_application_insights.core.connection_string
  }
  site_config {
    ftps_state                       = "Disabled"
    vnet_route_all_enabled           = true
    elastic_instance_minimum         = 1
    runtime_scale_monitoring_enabled = true
  }
  identity {
    type = "SystemAssigned"
  }
  tags = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}
