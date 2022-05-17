provider "azurerm" {
  features {}
}


resource "azurerm_template_deployment" "api_conn_eg" {
  name                = "armdeployment-eg-api-conn11"
  resource_group_name = var.resource_group_name
  template_body       = file("${path.module}/api-conn-eventgrid-template.json")
  deployment_mode     = "Incremental"

  parameters = {
    "connections_azureeventgridpublish_name" = "azureeventgridpublish",
    "api_key"                                = azurerm_eventgrid_topic.egt_update_status_topic.primary_access_key,
    "subscription_id"                        = var.subscription_id,
    "endpoint"                               = azurerm_eventgrid_topic.egt_update_status_topic.endpoint,
  }

}

resource "azurerm_template_deployment" "api_conn_sb" {
  name                = "armdeployment-sb-api-conn11"
  resource_group_name = var.resource_group_name
  template_body       = file("${path.module}/api-conn-sb-template.json")
  deployment_mode     = "Incremental"

  parameters = {
    "connections_servicebus_name" = "servicebus",
    "conn_string"                 = azurerm_servicebus_namespace.airlock_sb.default_primary_connection_string
    "subscription_id"             = var.subscription_id
  }
}


resource "azurerm_template_deployment" "ellogicapp" {
  name                = "armdeployment-logicapp11"
  resource_group_name = var.resource_group_name
  template_body       = file("${path.module}/logicapp-template.json")
  deployment_mode     = "Incremental"

  depends_on = [
    azurerm_template_deployment.api_conn_eg,
    azurerm_template_deployment.api_conn_sb

  ]
  parameters = {
    "connections_azureeventgridpublish_externalid" = azurerm_template_deployment.api_conn_eg.outputs["resourceid"],
    "connections_servicebus_1_externalid"          = azurerm_template_deployment.api_conn_sb.outputs["resourceid"],
    "workflows_newlogapp_name"                     = local.logic_app_name,
    "subscription_id"                              = var.subscription_id
  }

}


