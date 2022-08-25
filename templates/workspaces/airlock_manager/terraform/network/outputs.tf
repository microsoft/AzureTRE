output "services_subnet_id" {
  value = azurerm_subnet.services.id
}

output "vaultcore_zone_id" {
  value = data.azurerm_private_dns_zone.vaultcore.id
}

output "filecore_zone_id" {
  value = data.azurerm_private_dns_zone.filecore.id
}

output "blobcore_zone_id" {
  value = data.azurerm_private_dns_zone.blobcore.id
}

output "airlock_processor_subnet_id" {
  value = data.azurerm_subnet.airlockprocessor.id
}
