# For recommended Azure private DNS zone names see https://docs.microsoft.com/azure/private-link/private-endpoint-dns#azure-services-dns-zone-configuration

# Azure Monitor requires 5 DNS zones:
# - privatelink.monitor.azure.com
# - privatelink.oms.opinsights.azure.com
# - privatelink.ods.opinsights.azure.com
# - privatelink.agentsvc.azure-automation.net
# - privatelink.blob.core.windows.net (used also by Storage module)
# - privatelink.dfs.core.windows.net
resource "azurerm_private_dns_zone" "azure_monitor" {
  name                = "privatelink.monitor.azure.com"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor.name
  registration_enabled  = false
  tags                  = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azure_monitor_oms_opinsights" {
  name                = "privatelink.oms.opinsights.azure.com"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor_oms_opinsights" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor_oms_opinsights.name
  registration_enabled  = false
  tags                  = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azure_monitor_ods_opinsights" {
  name                = "privatelink.ods.opinsights.azure.com"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor_ods_opinsights" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor_ods_opinsights.name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azure_monitor_agentsvc" {
  name                = "privatelink.agentsvc.azure-automation.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_monitor_agentsvc" {
  name                  = "azure-monitor-link"
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.azure_monitor_agentsvc.name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

# Blob DNS zone is used by both Azure Monitor and Storage modules
resource "azurerm_private_dns_zone" "blobcore" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "blobcore" {
  name                  = "blobcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blobcore.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "dfscore" {
  name                = "privatelink.dfs.core.windows.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "dfscore" {
  name                  = "dfscorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.dfscore.name
  virtual_network_id    = azurerm_virtual_network.core.id

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azurewebsites" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azurewebsites" {
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.azurewebsites.name
  name                  = "azurewebsites-link"
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "mysql" {
  name                = "privatelink.mysql.database.azure.com"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "mysql" {
  resource_group_name   = var.resource_group_name
  virtual_network_id    = azurerm_virtual_network.core.id
  private_dns_zone_name = azurerm_private_dns_zone.mysql.name
  name                  = "azurewebsites-link"
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "static_web" {
  name                = "privatelink.web.core.windows.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "webcorelink" {
  name                  = "staticwebcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.static_web.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "filecore" {
  name                = "privatelink.file.core.windows.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "filecorelink" {
  name                  = "filecorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.filecore.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "vaultcore" {
  name                = "privatelink.vaultcore.azure.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "vaultcore" {
  name                  = "vaultcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.vaultcore.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azurecr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "acrlink" {
  name                  = "acrcorelink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.azurecr.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azureml" {
  name                = "privatelink.api.azureml.ms"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "azuremlcert" {
  name                = "privatelink.cert.api.azureml.ms"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "notebooks" {
  name                = "privatelink.notebooks.azure.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "nexus" {
  name                = "nexus-${var.tre_id}.${var.location}.cloudapp.azure.com"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "eventgrid" {
  name                = "privatelink.eventgrid.azure.net"
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "eventgridlink" {
  name                  = "eventgrid-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.eventgrid.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone" "private_dns_zones" {
  for_each            = local.private_dns_zone_names
  name                = each.key
  resource_group_name = var.resource_group_name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "private_dns_zone_links" {
  for_each              = azurerm_private_dns_zone.private_dns_zones
  name                  = each.value.name
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = each.value.name
  virtual_network_id    = azurerm_virtual_network.core.id
  tags                  = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}
