output "core_vnet_id" {
  value = azurerm_virtual_network.core.id
}

output "bastion_subnet_id" {
  value = azurerm_subnet.bastion.id
}

output "azure_firewall_subnet_id" {
  value = azurerm_subnet.azure_firewall.id
}

output "app_gw_subnet_id" {
  value = azurerm_subnet.app_gw.id
}

output "web_app_subnet_id" {
  value = azurerm_subnet.web_app.id
}

output "shared_subnet_id" {
  value = azurerm_subnet.shared.id
}

output "airlock_processor_subnet_id" {
  value = azurerm_subnet.airlock_processor.id
}

output "airlock_storage_subnet_id" {
  value = azurerm_subnet.airlock_storage.id
}

output "airlock_events_subnet_id" {
  value = azurerm_subnet.airlock_events.id
}

output "resource_processor_subnet_id" {
  value = azurerm_subnet.resource_processor.id
}

output "mysql_gitea_shared_service_subnet_id" {
  value = azurerm_subnet.mysql_gitea_shared_service.id
}

output "gateway_subnet_address_prefix" {
  value = local.gateway_subnet_address_prefix
}

# DNS Zones

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

output "file_core_dns_zone_id" {
  value = azurerm_private_dns_zone.filecore.id
}

output "queue_core_dns_zone_id" {
  value = azurerm_private_dns_zone.private_dns_zones["privatelink.queue.core.windows.net"].id
}

output "table_core_dns_zone_id" {
  value = azurerm_private_dns_zone.private_dns_zones["privatelink.table.core.windows.net"].id
}
