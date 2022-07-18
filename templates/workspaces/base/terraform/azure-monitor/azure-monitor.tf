resource "azurerm_log_analytics_workspace" "workspace" {
  name                = "log-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  retention_in_days   = 30
  sku                 = "PerGB2018"
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_log_analytics_linked_storage_account" "workspace_storage_ingestion" {
  data_source_type      = "ingestion"
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.workspace.id
  storage_account_ids   = [azurerm_storage_account.app_insights.id]
}

resource "azurerm_log_analytics_linked_storage_account" "workspace_storage_customlogs" {
  data_source_type      = "customlogs"
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.workspace.id
  storage_account_ids   = [azurerm_storage_account.app_insights.id]
}


# Storage account for Application Insights
# Because Private Link is enabled on Application Performance Management (APM), Bring Your Own Storage (BYOS) approach is required
resource "azurerm_storage_account" "app_insights" {
  name                            = lower(replace("stai${var.tre_id}ws${local.short_workspace_id}", "-", ""))
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  tags                            = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

data "local_file" "app_insights_arm_template" {
  filename = "${path.module}/app_insights.json"
}

# Application Insights
# Deployed using ARM template, because Terraform's azurerm_application_insights does not support linked storage account
resource "azurerm_resource_group_template_deployment" "app_insights_workspace" {
  name                = local.app_insights_name
  resource_group_name = var.resource_group_name
  deployment_mode     = "Incremental"
  template_content    = data.local_file.app_insights_arm_template.content

  parameters_content = jsonencode({
    "app_insights_name" = {
      value = local.app_insights_name
    }
    "location" = {
      value = var.location
    }
    "log_analytics_workspace_id" = {
      value = azurerm_log_analytics_workspace.workspace.id
    }
    "application_type" = {
      value = "web"
    }
    "storage_account_name" = {
      value = azurerm_storage_account.app_insights.name
    }
    "tre_core_tags" = {
      value = var.tre_workspace_tags
    }
  })
}

# resource "azurerm_monitor_private_link_scope" "ampls" {
#   name                = "ampls-${var.tre_id}-ws-${local.short_workspace_id}"
#   resource_group_name = var.resource_group_name
#   depends_on = [
#     azurerm_resource_group_template_deployment.app_insights_workspace,
#     azurerm_storage_account.app_insights,
#     azurerm_log_analytics_workspace.workspace
#   ]
# }
# resource "azurerm_monitor_private_link_scoped_service" "ampls_log_analytics" {
#   name                = "${azurerm_log_analytics_workspace.workspace.name}-ws-${local.short_workspace_id}-connection"
#   resource_group_name = var.resource_group_name
#   scope_name          = azurerm_monitor_private_link_scope.ampls.name
#   linked_resource_id  = azurerm_log_analytics_workspace.workspace.id
# }
# resource "azurerm_monitor_private_link_scoped_service" "ampls_app_insights" {
#   name                = "${local.app_insights_name}-ws-${local.short_workspace_id}-connection"
#   resource_group_name = var.resource_group_name
#   scope_name          = azurerm_monitor_private_link_scope.ampls.name
#   linked_resource_id  = jsondecode(azurerm_resource_group_template_deployment.app_insights_workspace.output_content).appInsightsId.value
# }

data "local_file" "ampls_arm_template" {
  filename = "${path.module}/ampls.json"
}
resource "azurerm_resource_group_template_deployment" "ampls" {
  name                = "ampls-${var.tre_id}"
  resource_group_name = var.resource_group_name
  deployment_mode     = "Incremental"
  template_content    = data.local_file.ampls_arm_template.content


  parameters_content = jsonencode({
    "private_link_scope_name" = {
      value = "ampls-${var.tre_id}-ws-${local.short_workspace_id}"
    }
    "workspace_name" = {
      value = azurerm_log_analytics_workspace.workspace.name
    }
    "app_insights_name" = {
      value = local.app_insights_name
    }
    "tre_workspace_tags" = {
      value = var.tre_workspace_tags
    }
  })

  depends_on = [
    azurerm_log_analytics_workspace.workspace,
    azurerm_resource_group_template_deployment.app_insights_workspace
  ]
}

resource "azurerm_private_endpoint" "azure_monitor_private_endpoint" {
  name                = "pe-ampls-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.workspace_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    # private_connection_resource_id = azurerm_monitor_private_link_scope.ampls.id
    private_connection_resource_id = jsondecode(azurerm_resource_group_template_deployment.ampls.output_content).resourceId.value
    name                           = "psc-ampls-${var.tre_id}-ws-${local.short_workspace_id}"
    subresource_names              = ["azuremonitor"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name = "azure-monitor-private-dns-zone-group"

    private_dns_zone_ids = [
      var.azure_monitor_dns_zone_id,
      var.azure_monitor_oms_opinsights_dns_zone_id,
      var.azure_monitor_ods_opinsights_dns_zone_id,
      var.azure_monitor_agentsvc_dns_zone_id,
      var.blob_core_dns_zone_id,
    ]
  }

  depends_on = [
    azurerm_resource_group_template_deployment.ampls
    # azurerm_monitor_private_link_scope.ampls
  ]
}
