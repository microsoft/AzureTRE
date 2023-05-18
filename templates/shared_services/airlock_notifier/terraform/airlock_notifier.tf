resource "azurerm_service_plan" "notifier_plan" {
  name                = "airlock-notifier-plan-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
  location            = data.azurerm_resource_group.core.location
  sku_name            = "WS1"
  os_type             = "Windows"
  tags                = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_servicebus_queue" "notifications_queue" {
  name         = "notifications"
  namespace_id = data.azurerm_servicebus_namespace.core.id

  enable_partitioning = false
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

// Using ARM as terraform's azurerm_api_connection creates a v1 api connection,
// without connectionRuntimeUrl needed for SMTP https://github.com/hashicorp/terraform-provider-azurerm/issues/16195
resource "azurerm_resource_group_template_deployment" "smtp_api_connection" {
  name                = "smtp-api-connection"
  resource_group_name = data.azurerm_resource_group.core.name

  template_content = data.local_file.smtp_api_connection.content


  parameters_content = jsonencode({
    "serverAddress" = {
      value = var.smtp_server_address
    },
    "userName" = {
      value = var.smtp_username
    },
    "password" = {
      value = var.smtp_password
    },
    "enableSSL" = {
      value = var.smtp_server_enable_ssl
    },
    "serverPort" = {
      value = var.server_port
    }
  })

  deployment_mode = "Incremental"
  tags            = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_logic_app_standard" "logic_app" {
  name                       = "airlock-notifier-app-${var.tre_id}"
  location                   = data.azurerm_resource_group.core.location
  resource_group_name        = data.azurerm_resource_group.core.name
  app_service_plan_id        = azurerm_service_plan.notifier_plan.id
  storage_account_name       = data.azurerm_storage_account.storage.name
  storage_account_access_key = data.azurerm_storage_account.storage.primary_access_key
  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"              = "node"
    "WEBSITE_NODE_DEFAULT_VERSION"          = "~12"
    "serviceBus_connectionString"           = data.azurerm_servicebus_namespace.core.default_primary_connection_string
    "subscription"                          = data.azurerm_subscription.current.subscription_id
    "resource_group"                        = data.azurerm_resource_group.core.name
    "smtp_connection_runtime_url"           = jsondecode(azurerm_resource_group_template_deployment.smtp_api_connection.output_content).connectionRuntimeUrl.value
    "smtp_from_email"                       = var.smtp_from_email
    "tre_url"                               = var.tre_url != "" ? var.tre_url : local.default_tre_url
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = data.azurerm_application_insights.core.connection_string
  }
  site_config {
    ftps_state               = "Disabled"
    vnet_route_all_enabled   = true
    elastic_instance_minimum = 1
  }
  identity {
    type = "SystemAssigned"
  }
  tags = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_resource_group_template_deployment" "smtp_api_connection_access_policy" {
  name                = "smtp-api-connection-access-policy"
  resource_group_name = data.azurerm_resource_group.core.name

  template_content = data.local_file.smtp_access_policy.content


  parameters_content = jsonencode({
    "servicePrincipalId" = {
      value = azurerm_logic_app_standard.logic_app.identity[0].principal_id
    },
    "servicePrincipalTenantId" = {
      value = azurerm_logic_app_standard.logic_app.identity[0].tenant_id
    }
  })

  deployment_mode = "Incremental"
  tags            = local.tre_shared_service_tags
  lifecycle { ignore_changes = [tags] }
}


resource "azurerm_app_service_virtual_network_swift_connection" "airlock_notifier_integrated_vnet" {
  app_service_id = azurerm_logic_app_standard.logic_app.id
  subnet_id      = data.azurerm_subnet.airlock_notification.id
}
