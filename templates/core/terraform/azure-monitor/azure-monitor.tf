# Log Analytics
resource "azurerm_log_analytics_workspace" "core" {
  name                       = "log-${var.tre_id}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  retention_in_days          = 30
  sku                        = "PerGB2018"
  tags                       = var.tre_core_tags
  internet_ingestion_enabled = var.enable_local_debugging ? true : false

  lifecycle { ignore_changes = [tags] }
}

# Storage account for Azure Monitor ingestion
# Because Private Link is enabled on Application Performance Management (APM), Bring Your Own Storage (BYOS) approach is required
resource "azurerm_storage_account" "az_monitor" {
  name                            = lower(replace("stazmonitor${var.tre_id}", "-", ""))
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  tags                            = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_log_analytics_linked_storage_account" "workspace_storage_ingestion" {
  data_source_type      = "ingestion"
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.core.id
  storage_account_ids   = [azurerm_storage_account.az_monitor.id]
}

resource "azurerm_log_analytics_linked_storage_account" "workspace_storage_customlogs" {
  data_source_type      = "customlogs"
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.core.id
  storage_account_ids   = [azurerm_storage_account.az_monitor.id]
}

resource "azurerm_monitor_private_link_scope" "ampls_core" {
  name                = "ampls-${var.tre_id}"
  resource_group_name = var.resource_group_name
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_private_link_scoped_service" "ampls_log_anaytics" {
  name                = "ampls-log-anaytics-service"
  resource_group_name = var.resource_group_name
  scope_name          = azurerm_monitor_private_link_scope.ampls_core.name
  linked_resource_id  = azurerm_log_analytics_workspace.core.id
}



# Application Insights

resource "azurerm_application_insights" "core" {
  name                                = "appi-${var.tre_id}"
  location                            = var.location
  resource_group_name                 = var.resource_group_name
  workspace_id                        = azurerm_log_analytics_workspace.core.id
  application_type                    = "web"
  internet_ingestion_enabled          = var.enable_local_debugging ? true : false
  force_customer_storage_for_profiler = true
  tags                                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_private_link_scoped_service" "ampls_app_insights" {
  name                = "ampls-app-insights-service"
  resource_group_name = var.resource_group_name
  scope_name          = azurerm_monitor_private_link_scope.ampls_core.name
  linked_resource_id  = azurerm_application_insights.core.id
}

resource "azurerm_private_endpoint" "azure_monitor_private_endpoint" {
  name                = "pe-ampls-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.shared_subnet_id
  tags                = var.tre_core_tags

  lifecycle { ignore_changes = [tags] }
  depends_on = [
    azurerm_monitor_private_link_scoped_service.ampls_app_insights,
  ]

  private_service_connection {
    private_connection_resource_id = azurerm_monitor_private_link_scope.ampls_core.id
    name                           = "psc-ampls-${var.tre_id}"
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
      var.blob_core_dns_zone_id
    ]
  }
}
