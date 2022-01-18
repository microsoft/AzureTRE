output "core_vnet_id" {
  value = azurerm_virtual_network.core.id
}

output "subnet_ids" {
  value = {
    "bastion"            = azurerm_subnet.bastion.id
    "azure_firewall"     = azurerm_subnet.azure_firewall.id
    "app_gw"             = azurerm_subnet.app_gw.id
    "web_app"            = azurerm_subnet.web_app.id
    "shared"             = azurerm_subnet.shared.id
    "resource_processor" = azurerm_subnet.resource_processor.id
  }
}

output "azure_monitor_dns_zone_id" {
  value = azurerm_private_dns_zone.azure_monitor.id
}

output "azure_monitor_oms_opinsights_dns_zone_id" {
  value = azurerm_private_dns_zone.azure_monitor_oms_opinsights.id
}

output "azure_monitor_ods_opinsights_dns_zone_id" {
  value = azurerm_private_dns_zone.azure_monitor_ods_opinsights.id
}

output "azure_monitor_agentsvc_dns_zone_id" {
  value = azurerm_private_dns_zone.azure_monitor_agentsvc.id
}

output "blob_core_dns_zone_id" {
  value = azurerm_private_dns_zone.blobcore.id
}

output "azurewebsites_dns_zone_id" {
  value = azurerm_private_dns_zone.azurewebsites.id
}

output "static_web_dns_zone_id" {
  value = azurerm_private_dns_zone.static_web.id
}
