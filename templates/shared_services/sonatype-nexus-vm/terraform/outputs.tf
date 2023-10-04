output "nexus_allowed_fqdns_list" {
  value = jsonencode(local.nexus_allowed_fqdns_list)
}

output "workspace_vm_allowed_fqdns_list" {
  value = jsonencode(local.workspace_vm_allowed_fqdns_list)
}

output "private_ip_addresses" {
  value = jsonencode(azurerm_network_interface.nexus.private_ip_addresses)
}

output "connection_uri" {
  value = "https://${data.azurerm_private_dns_zone.nexus.name}"
}

output "is_exposed_externally" {
  value = false
}
