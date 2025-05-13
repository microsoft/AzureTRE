output "core_vnet_id" {
  value = azurerm_virtual_network.core.id
}

output "bastion_subnet_id" {
  value = local.subnet_ids_map["AzureBastionSubnet"]
}

output "azure_firewall_subnet_id" {
  value = local.subnet_ids_map["AzureFirewallSubnet"]
}

output "app_gw_subnet_id" {
  value = local.subnet_ids_map["AppGwSubnet"]
}

output "web_app_subnet_id" {
  value = local.subnet_ids_map["WebAppSubnet"]
}

output "shared_subnet_id" {
  value = local.subnet_ids_map["SharedSubnet"]
}

output "airlock_processor_subnet_id" {
  value = local.subnet_ids_map["AirlockProcessorSubnet"]
}

output "airlock_storage_subnet_id" {
  value = local.subnet_ids_map["AirlockStorageSubnet"]
}

output "airlock_events_subnet_id" {
  value = local.subnet_ids_map["AirlockEventsSubnet"]
}

output "resource_processor_subnet_id" {
  value = local.subnet_ids_map["ResourceProcessorSubnet"]
}

output "airlock_notification_subnet_id" {
  value = local.subnet_ids_map["AirlockNotifiactionSubnet"]
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


output "azurecr_dns_zone_id" {
  value = azurerm_private_dns_zone.azurecr.id
}
