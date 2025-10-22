resource "azurerm_logic_app_workflow" "cert_renewal" {
  count               = var.enable_auto_renewal ? 1 : 0
  name                = "logicapp-cert-renewal-${local.service_resource_name_suffix}"
  location            = local.location
  resource_group_name = local.resource_group_name
  tags                = local.tre_shared_service_tags

  workflow_schema     = "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
  workflow_version    = "1.0.0.0"

  parameters = {
    "keyvault_name" = {
      "defaultValue" = data.azurerm_key_vault.core.name
      "type"         = "String"
    }
    "cert_name" = {
      "defaultValue" = var.cert_name
      "type"         = "String"
    }
    "renewal_threshold_days" = {
      "defaultValue" = var.renewal_threshold_days
      "type"         = "Int"
    }
    "tre_api_base_url" = {
      "defaultValue" = local.tre_api_base_url
      "type"         = "String"
    }
    "shared_service_id" = {
      "defaultValue" = var.tre_resource_id
      "type"         = "String"
    }
  }

  # Basic workflow definition - will be replaced by ARM template deployment
  workflow_definition = jsonencode({
    "$schema" = "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
    contentVersion = "1.0.0.0"
    parameters = {
      "keyvault_name" = {
        "defaultValue" = data.azurerm_key_vault.core.name
        "type" = "String"
      }
      "cert_name" = {
        "defaultValue" = var.cert_name
        "type" = "String"
      }
      "renewal_threshold_days" = {
        "defaultValue" = var.renewal_threshold_days
        "type" = "Int"
      }
      "tre_api_base_url" = {
        "defaultValue" = local.tre_api_base_url
        "type" = "String"
      }
      "shared_service_id" = {
        "defaultValue" = var.tre_resource_id
        "type" = "String"
      }
    }
    triggers = {
      "Scheduled_Certificate_Check" = {
        "recurrence" = {
          "frequency" = "Week"
          "interval" = 1
          "schedule" = {
            "hours" = [2]
            "minutes" = [0]
            "weekDays" = ["Sunday"]
          }
        }
        "type" = "Recurrence"
      }
    }
    actions = {
      "Initialize_variable" = {
        "runAfter" = {}
        "type" = "InitializeVariable"
        "inputs" = {
          "variables" = [
            {
              "name" = "certificateExpiryDate"
              "type" = "string"
            }
          ]
        }
      }
    }
    outputs = {}
  })

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "cert_renewal_keyvault" {
  count                = var.enable_auto_renewal ? 1 : 0
  scope                = data.azurerm_key_vault.core.id
  role_definition_name = "Key Vault Certificates Officer"
  principal_id         = azurerm_logic_app_workflow.cert_renewal[0].identity[0].principal_id
}

resource "azurerm_role_assignment" "cert_renewal_api" {
  count                = var.enable_auto_renewal ? 1 : 0
  scope                = data.azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_logic_app_workflow.cert_renewal[0].identity[0].principal_id
}

# Deploy the complete Logic App workflow using ARM template
resource "azurerm_resource_group_template_deployment" "cert_renewal_workflow" {
  count               = var.enable_auto_renewal ? 1 : 0
  name                = "cert-renewal-workflow-deployment-${local.service_resource_name_suffix}"
  resource_group_name = local.resource_group_name
  deployment_mode     = "Incremental"

  template_content = templatefile("${path.module}/logic_app_workflow.json", {
    workflow_name           = azurerm_logic_app_workflow.cert_renewal[0].name
    location               = local.location
    keyvault_name          = data.azurerm_key_vault.core.name
    cert_name              = var.cert_name
    renewal_threshold_days = var.renewal_threshold_days
    tre_api_base_url       = local.tre_api_base_url
    shared_service_id      = var.tre_resource_id
    cron_expression        = var.renewal_schedule_cron
  })

  depends_on = [
    azurerm_logic_app_workflow.cert_renewal,
    azurerm_role_assignment.cert_renewal_keyvault,
    azurerm_role_assignment.cert_renewal_api
  ]
}