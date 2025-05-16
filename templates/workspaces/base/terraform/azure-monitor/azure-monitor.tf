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
  name                             = lower(replace("stai${var.tre_id}ws${local.short_workspace_id}", "-", ""))
  resource_group_name              = var.resource_group_name
  location                         = var.location
  account_kind                     = "StorageV2"
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  table_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  queue_encryption_key_type        = var.enable_cmk_encryption ? "Account" : "Service"
  allow_nested_items_to_be_public  = false
  cross_tenant_replication_enabled = false
  local_user_enabled               = false
  tags                             = var.tre_workspace_tags

  # unclear the implications on az-monitor, so leaving it for now.
  # shared_access_key_enabled        = false

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.encryption_identity_id]
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id          = var.encryption_key_versionless_id
      user_assigned_identity_id = var.encryption_identity_id
    }
  }

  # changing this value is destructive, hence attribute is in lifecycle.ignore_changes block below
  infrastructure_encryption_enabled = true

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  lifecycle { ignore_changes = [infrastructure_encryption_enabled, tags] }
}

resource "azurerm_log_analytics_linked_storage_account" "workspace_storage_ingestion" {
  data_source_type      = "Ingestion"
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.workspace.id
  storage_account_ids   = [azurerm_storage_account.app_insights.id]
}

resource "azurerm_log_analytics_linked_storage_account" "workspace_storage_customlogs" {
  data_source_type      = "CustomLogs"
  resource_group_name   = var.resource_group_name
  workspace_resource_id = azurerm_log_analytics_workspace.workspace.id
  storage_account_ids   = [azurerm_storage_account.app_insights.id]
}

# TODO: Switch to azurerm once the followiung issue is resolved: https://github.com/microsoft/AzureTRE/issues/3625
# resource "azurerm_monitor_private_link_scope" "workspace" {
#   name                = "ampls-${var.tre_id}-ws-${local.short_workspace_id}"
#   resource_group_name = var.resource_group_name
#   tags                = var.tre_workspace_tags

#   lifecycle { ignore_changes = [tags] }
# }

resource "azapi_resource" "ampls_workspace" {
  type      = "microsoft.insights/privateLinkScopes@2021-07-01-preview"
  name      = "ampls-${var.tre_id}-ws-${local.short_workspace_id}"
  parent_id = var.resource_group_id
  location  = "global"
  tags      = var.tre_workspace_tags

  body = {
    properties = {
      accessModeSettings = {
        ingestionAccessMode = "PrivateOnly"
        queryAccessMode     = "PrivateOnly"
      }
    }
  }

  response_export_values = [
    "id"
  ]


  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_private_link_scoped_service" "ampls_log_anaytics" {
  name                = "ampls-log-anaytics-service"
  resource_group_name = var.resource_group_name
  scope_name          = azapi_resource.ampls_workspace.name
  linked_resource_id  = azurerm_log_analytics_workspace.workspace.id
}



# Application Insights

# TODO: switch from the azapi implementation to azurerm when resolved https://github.com/microsoft/AzureTRE/issues/3200
# resource "azurerm_application_insights" "workspace" {
#   name                                = local.app_insights_name
#   location                            = var.location
#   resource_group_name                 = var.resource_group_name
#   workspace_id                        = azurerm_log_analytics_workspace.workspace.id
#   application_type                    = "web"
#   internet_ingestion_enabled          = var.enable_local_debugging ? true : false
#   force_customer_storage_for_profiler = true
#   tags                                = var.tre_workspace_tags

#   lifecycle { ignore_changes = [tags] }
# }

resource "azapi_resource" "appinsights" {
  type      = "Microsoft.Insights/components@2020-02-02"
  name      = local.app_insights_name
  parent_id = var.resource_group_id
  location  = var.location
  tags      = var.tre_workspace_tags

  body = {
    kind = "web"
    properties = {
      Application_Type                = "web"
      Flow_Type                       = "Bluefield"
      Request_Source                  = "rest"
      IngestionMode                   = "LogAnalytics"
      WorkspaceResourceId             = azurerm_log_analytics_workspace.workspace.id
      ForceCustomerStorageForProfiler = true
      publicNetworkAccessForIngestion = var.enable_local_debugging ? "Enabled" : "Disabled"
    }
  }

  response_export_values = [
    "id",
    "properties.ConnectionString",
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_monitor_private_link_scoped_service" "ampls_app_insights" {
  name                = "ampls-app-insights-service"
  resource_group_name = var.resource_group_name
  scope_name          = azapi_resource.ampls_workspace.name

  linked_resource_id = azapi_resource.appinsights.id
}

resource "azurerm_private_endpoint" "azure_monitor_private_endpoint" {
  name                = "pe-ampls-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.workspace_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    private_connection_resource_id = azapi_resource.ampls_workspace.id
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
  name                = "${local.app_insights_name}-failure-anomalies-action-group"
  resource_group_name = var.resource_group_name
  short_name          = "Failures"
  tags                = var.tre_workspace_tags
  depends_on = [
    # azurerm_application_insights.workspace
    azapi_resource.appinsights
  ]

  lifecycle { ignore_changes = [tags] }
}

# We don't really need this, but if not present the RG will not be empty and won't be destroyed
# TODO: remove when this is resolved: https://github.com/hashicorp/terraform-provider-azurerm/issues/18026
resource "azurerm_monitor_smart_detector_alert_rule" "failure_anomalies" {
  name                = "Failure Anomalies - ${local.app_insights_name}"
  resource_group_name = var.resource_group_name
  severity            = "Sev3"
  scope_resource_ids = [
    azapi_resource.appinsights.id
  ]
  frequency     = "PT1M"
  detector_type = "FailureAnomaliesDetector"
  tags          = var.tre_workspace_tags

  action_group {
    ids = [azurerm_monitor_action_group.failure_anomalies.id]
  }

  lifecycle { ignore_changes = [tags] }
}
