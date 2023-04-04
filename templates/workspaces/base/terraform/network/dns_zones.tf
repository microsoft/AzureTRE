# For recommended Azure private DNS zone names see https://docs.microsoft.com/azure/private-link/private-endpoint-dns#azure-services-dns-zone-configuration

# To enable connecting to Azure Monitor from within a workspace VNET (where traffic is restricted), we need to have an Azure Monitor Private Link Scope (AMPLS) that is connected to a Private Endpoint within the VNET.
# An AMPLS can be connected to multiple Private Endpoints and multiple Azure Monitor resources, but [an AMPLS can only connect to up to 10 Private Endpoints](https://docs.microsoft.com/en-us/azure/azure-monitor/logs/private-link-design#consider-ampls-limits) so the suggestion is to deploy an AMPLS per workspace for simplicity.
# Because there are some shared endpoints (i.e. not resource-specific), a [single AMPLS should be used for all VNETs that share the same DNS](https://docs.microsoft.com/en-us/azure/azure-monitor/logs/private-link-security#azure-monitor-private-links-rely-on-your-dns). Currently, we have separate VNETs for each workspace but each VNET is linked to the same, single private DNS Zone for Azure Monitor/App Insights. To enable an AMPLS per workspace, we need to update the private DNS Zones for Azure Monitor so that the existing zones are just used for the core VNET and deploy separate zones for each workspace.


# Azure Monitor requires 5 DNS zones:
# - privatelink.monitor.azure.com
# - privatelink.oms.opinsights.azure.com
# - privatelink.ods.opinsights.azure.com
# - privatelink.agentsvc.azure-automation.net
# - privatelink.blob.core.windows.net (used also by Storage module)
resource "azurerm_private_dns_zone" "azure_monitor" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.monitor.azure.com"]
  resource_group_name = var.ws_resource_group_name
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.ws_resource_group_name
  virtual_network_id    = azurerm_virtual_network.ws.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor.name
  registration_enabled  = false
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azure_monitor_oms_opinsights" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.oms.opinsights.azure.com"]
  resource_group_name = var.ws_resource_group_name
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor_oms_opinsights" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.ws_resource_group_name
  virtual_network_id    = azurerm_virtual_network.ws.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor_oms_opinsights.name
  registration_enabled  = false
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azure_monitor_ods_opinsights" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.ods.opinsights.azure.com"]
  resource_group_name = var.ws_resource_group_name
  tags                = var.tre_workspace_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor_ods_opinsights" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.ws_resource_group_name
  virtual_network_id    = azurerm_virtual_network.ws.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor_ods_opinsights.name
  registration_enabled  = false
  tags                  = var.tre_workspace_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azure_monitor_agentsvc" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.agentsvc.azure-automation.net"]
  resource_group_name = var.ws_resource_group_name
  tags                = var.tre_workspace_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor_agentsvc" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.ws_resource_group_name
  virtual_network_id    = azurerm_virtual_network.ws.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor_agentsvc.name
  registration_enabled  = false
  tags                  = var.tre_workspace_tags
  lifecycle { ignore_changes = [tags] }
}
