resource "azurerm_log_analytics_workspace" "core" {
  name                = "log-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  retention_in_days   = 30
  sku                 = "pergb2018"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  workspace_id        = azurerm_log_analytics_workspace.core.id
  application_type    = "web"

  lifecycle { ignore_changes = [tags] }
}

data "local_file" "ampls_arm_template" {
  filename = "${path.module}/ampls.json"
}

resource "azurerm_resource_group_template_deployment" "ampls_core" {
  name                = "ampls-${var.tre_id}"
  resource_group_name = var.resource_group_name
  deployment_mode     = "Incremental"
  template_content    = data.local_file.ampls_arm_template.content

  parameters_content  = jsonencode({
    "private_link_scope_name" = {
      value = "ampls-${var.tre_id}"
    }
    "workspace_name" = {
      value = azurerm_log_analytics_workspace.core.name
    }
    "app_insights_name" = {
      value = azurerm_application_insights.core.name
    }
  })
}
