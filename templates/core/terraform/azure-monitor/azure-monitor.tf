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

resource "azurerm_resource_group_template_deployment" "ampls_core" {
  name                = "ampls-${var.tre_id}"
  resource_group_name = var.resource_group_name
  deployment_mode     = "Incremental"
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
  template_content = <<-EOT
    {
      "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
      "contentVersion": "1.0.0.0",
      "parameters": {
        "private_link_scope_name": {
          "type": "String"
        },
        "workspace_name": {
          "type": "String"
        },
        "app_insights_name": {
          "type": "String"
        }
      },
      "variables": {},
      "resources": [
        {
          "type": "microsoft.insights/privatelinkscopes",
          "apiVersion": "2021-07-01-preview",
          "name": "[parameters('private_link_scope_name')]",
          "location": "global",
          "properties": {
            "accessModeSettings": {
              "queryAccessMode":"Open",
              "ingestionAccessMode":"Open"
            }
          }
        },
        {
          "type": "microsoft.insights/privatelinkscopes/scopedresources",
          "apiVersion": "2019-10-17-preview",
          "name": "[concat(parameters('private_link_scope_name'), '/', concat(parameters('workspace_name'), '-connection'))]",
          "dependsOn": [
            "[resourceId('microsoft.insights/privatelinkscopes', parameters('private_link_scope_name'))]"
          ],
          "properties": {
            "linkedResourceId": "[resourceId('microsoft.operationalinsights/workspaces', parameters('workspace_name'))]"
          }
        },
        {
          "type": "microsoft.insights/privatelinkscopes/scopedresources",
          "apiVersion": "2019-10-17-preview",
          "name": "[concat(parameters('private_link_scope_name'), '/', concat(parameters('app_insights_name'), '-connection'))]",
          "dependsOn": [
            "[resourceId('microsoft.insights/privatelinkscopes', parameters('private_link_scope_name'))]"
          ],
          "properties": {
            "linkedResourceId": "[resourceId('microsoft.insights/components', parameters('app_insights_name'))]"
          }
        }
      ],
      "outputs": {
        "resourceID": {
          "type": "String",
          "value": "[resourceId('microsoft.insights/privatelinkscopes', parameters('private_link_scope_name'))]"
        }
      }
    }
  EOT
}
