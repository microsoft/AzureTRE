resource "azurerm_log_analytics_workspace" "core" {
  name                = "log-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  retention_in_days   = 30
  sku                 = "pergb2018"

  lifecycle { ignore_changes = [tags] }
}

# Storage account for Application Insights
# Because Private Link is enabled on Application Performance Management (APM), Bring Your Own Storage (BYOS) approach is required
resource "azurerm_storage_account" "app_insights" {
  name                            = lower(replace("stappinsights${var.tre_id}", "-", ""))
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

  lifecycle { ignore_changes = [tags] }
}

data "local_file" "app_insights_arm_template" {
  filename = "${path.module}/app_insights.json"
}

# Application Insights
# Deployed using ARM template, because Terraform's azurerm_application_insights does not support linked storage account
resource "azurerm_resource_group_template_deployment" "app_insights_core" {
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
      value = azurerm_log_analytics_workspace.core.id
    }
    "application_type" = {
      value = "web"
    }
    "storage_account_name" = {
      value = azurerm_storage_account.app_insights.name
    }
  })
}

data "local_file" "ampls_arm_template" {
  filename = "${path.module}/ampls.json"
}

# Azure Monitor Private Link Scope
# See https://docs.microsoft.com/azure/azure-monitor/logs/private-link-security
resource "azurerm_resource_group_template_deployment" "ampls_core" {
  name                = "ampls-${var.tre_id}"
  resource_group_name = var.resource_group_name
  deployment_mode     = "Incremental"
  template_content    = data.local_file.ampls_arm_template.content

  parameters_content = jsonencode({
    "private_link_scope_name" = {
      value = "ampls-${var.tre_id}"
    }
    "workspace_name" = {
      value = azurerm_log_analytics_workspace.core.name
    }
    "app_insights_name" = {
      value = local.app_insights_name
    }
  })

  depends_on = [
    azurerm_log_analytics_workspace.core,
    azurerm_resource_group_template_deployment.app_insights_core
  ]
}

resource "azurerm_private_endpoint" "azure_monitor_private_endpoint" {
  name                = "pe-ampls-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.shared_subnet_id

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    private_connection_resource_id = jsondecode(azurerm_resource_group_template_deployment.ampls_core.output_content).resourceId.value
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
