resource "azurerm_service_plan" "notifier-plan" {
  name                = "airlock-notifier-plan-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
  location            = data.azurerm_resource_group.core.location
  sku_name            = "WS1"
  os_type             = "Windows"
}


resource "azurerm_servicebus_queue" "notifications_queue" {
  name         = "notifications"
  namespace_id = data.azurerm_servicebus_namespace.core.id

  enable_partitioning = false
}

// Using ARM as terraform's azurerm_api_connection creates a v1 api connection,
// without connectionRuntimeUrl needed for SMTP https://github.com/hashicorp/terraform-provider-azurerm/issues/16195
resource "azurerm_resource_group_template_deployment" "smtp-api-connection" {
  name                = "smtp-api-connection"
  resource_group_name = data.azurerm_resource_group.core.name

  template_content = data.local_file.smtp-api-connection.content


  parameters_content = jsonencode({
    "serverAddress" = {
      value = var.smtp_server_address
    },
    "userName" = {
      value = var.smtp_username
    },
    "password" = {
      value = var.smtp_password
    }
  })

  deployment_mode = "Incremental"

}

resource "azurerm_logic_app_standard" "logic-app" {
  name                       = "airlock-notifier-app-${var.tre_id}"
  location                   = data.azurerm_resource_group.core.location
  resource_group_name        = data.azurerm_resource_group.core.name
  app_service_plan_id        = azurerm_service_plan.notifier-plan.id
  storage_account_name       = data.azurerm_storage_account.storage.name
  storage_account_access_key = data.azurerm_storage_account.storage.primary_access_key
  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "node"
    "WEBSITE_NODE_DEFAULT_VERSION"   = "~12"
    "serviceBus_connectionString"        = data.azurerm_servicebus_namespace.core.default_primary_connection_string
    "subscription"        = data.azurerm_subscription.current.subscription_id
    "resource_group"        = data.azurerm_resource_group.core.name
    "smtp_connection_runtime_url"    = jsondecode(azurerm_resource_group_template_deployment.smtp-api-connection.output_content).connectionRuntimeUrl.value
    "smtp_from_email"    = var.smtp_from_email
    "APPINSIGHTS_INSTRUMENTATIONKEY" = data.azurerm_application_insights.core.instrumentation_key
  }

  identity {
    type = "SystemAssigned"
  }

}


resource "azurerm_resource_group_template_deployment" "smtp-api-connection-access-policy" {
  name                = "smtp-api-connection-access-policy"
  resource_group_name = data.azurerm_resource_group.core.name

  template_content = data.local_file.smtp-access-policy.content


  parameters_content = jsonencode({
    "servicePrincipalId" = {
      value = azurerm_logic_app_standard.logic-app.identity.0.principal_id
    },
    "servicePrincipalTenantId" = {
      value = azurerm_logic_app_standard.logic-app.identity.0.tenant_id
    }
  })

  deployment_mode = "Incremental"

}

resource "null_resource" "deploy_app" {
  provisioner "local-exec" {
    command    = "az login --identity -u '${data.azurerm_client_config.current.client_id}' && az functionapp deployment source config-zip --name ${azurerm_logic_app_standard.logic-app.name} --resource-group ${azurerm_logic_app_standard.logic-app.resource_group_name} --subscription 73a4ea93-d914-424d-9e64-28adf397e8e3 --src /tmp/LogicApp.zip"
    on_failure = fail
  }

  triggers = {
    always_run = timestamp()
  }

  depends_on = [azurerm_logic_app_standard.logic-app]
}
