output "nexus_fqdn" {
  value = azurerm_private_dns_a_record.nexus_vm.fqdn
}

output "nexus_allowed_fqdns_list" {
  value = jsonencode(local.nexus_allowed_fqdns_list)
}

output "address_prefixes" {
  value = jsonencode(data.azurerm_subnet.shared.address_prefixes)
}

output "workspace_vm_allowed_fqdns_list" {
  value = jsonencode(local.workspace_vm_allowed_fqdns_list)
}

