resource "azurerm_log_analytics_workspace" "workspace" {
  name                       = "log-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  retention_in_days          = 30
  sku                        = "PerGB2018"
  tags                       = var.tre_workspace_tags
  internet_ingestion_enabled = var.enable_local_debugging ? true : false

  lifecycle { ignore_changes = [tags] }
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

resource "azurerm_monitor_private_link_scope" "workspace" {
  name                = "ampls-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = var.resource_group_name
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_private_link_scoped_service" "ampls_log_anaytics" {
  name                = "ampls-log-anaytics-service"
  resource_group_name = var.resource_group_name
  scope_name          = azurerm_monitor_private_link_scope.workspace.name
  linked_resource_id  = azurerm_log_analytics_workspace.workspace.id
}



# Application Insights

resource "azurerm_application_insights" "workspace" {
  name                                = "appi-${var.tre_id}-ws-${local.short_workspace_id}"
  location                            = var.location
  resource_group_name                 = var.resource_group_name
  workspace_id                        = azurerm_log_analytics_workspace.workspace.id
  application_type                    = "web"
  internet_ingestion_enabled          = var.enable_local_debugging ? true : false
  force_customer_storage_for_profiler = true
  tags                                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_private_link_scoped_service" "ampls_app_insights" {
  name                = "ampls-app-insights-service"
  resource_group_name = var.resource_group_name
  scope_name          = azurerm_monitor_private_link_scope.workspace.name
  linked_resource_id  = azurerm_application_insights.workspace.id
}

resource "azurerm_private_endpoint" "azure_monitor_private_endpoint" {
  count               = 0 # Remove with https://github.com/microsoft/AzureTRE/issues/2357
  name                = "pe-ampls-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.workspace_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    private_connection_resource_id = azurerm_monitor_private_link_scope.workspace.id
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
    azurerm_monitor_private_link_scoped_service.ampls_app_insights,
  ]
}

# We don't really need this, but if not present the RG will not be empty and won't be destroyed
# TODO: remove when this is resolved: https://github.com/hashicorp/terraform-provider-azurerm/issues/18026
resource "azurerm_monitor_action_group" "failure_anomalies" {
  name                = "${azurerm_application_insights.workspace.name}-failure-anomalies-action-group"
  resource_group_name = var.resource_group_name
  short_name          = "Failures"
}

# We don't really need this, but if not present the RG will not be empty and won't be destroyed
# TODO: remove when this is resolved: https://github.com/hashicorp/terraform-provider-azurerm/issues/18026
resource "azurerm_monitor_smart_detector_alert_rule" "failure_anomalies" {
  name                = "Failure Anomalies - ${local.app_insights_name}"
  resource_group_name = var.resource_group_name
  severity            = "Sev3"
  scope_resource_ids  = [azurerm_application_insights.workspace.id]
  frequency           = "PT1M"
  detector_type       = "FailureAnomaliesDetector"

  action_group {
    ids = [azurerm_monitor_action_group.failure_anomalies.id]
  }
}
