output "core_vnet_id" {
  value = azurerm_virtual_network.core.id
}

output "bastion_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AzureBastionSubnet"
}

output "azure_firewall_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AzureFirewallSubnet"
}

output "firewall_management_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AzureFirewallManagementSubnet"
}

output "app_gw_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AppGwSubnet"
}

output "web_app_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/WebAppSubnet"
}

output "shared_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/SharedSubnet"
}

output "resource_processor_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/ResourceProcessorSubnet"
}

output "airlock_processor_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AirlockProcessorSubnet"
}

output "airlock_notification_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AirlockNotifiactionSubnet"
}

output "airlock_storage_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AirlockStorageSubnet"
}

output "airlock_events_subnet_id" {
  value = "${azurerm_virtual_network.core.id}/subnets/AirlockEventsSubnet"
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

output "eventgrid_private_dns_zone_id" {
  value = azurerm_private_dns_zone.eventgrid.id
}

output "azurecr_dns_zone_id" {
  value = azurerm_private_dns_zone.azurecr.id
}

# IP Groups
output "resource_processor_ip_group_id" {
  value = azurerm_ip_group.resource_processor.id
}

output "shared_services_ip_group_id" {
  value = azurerm_ip_group.shared.id
}

output "airlock_processor_ip_group_id" {
  value = azurerm_ip_group.airlock_processor.id
}

output "web_app_ip_group_id" {
  value = azurerm_ip_group.webapp.id
}

