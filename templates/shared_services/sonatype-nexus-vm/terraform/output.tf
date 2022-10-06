output "nexus_fqdn" {
  value = azurerm_private_dns_a_record.nexus_vm.fqdn
}

output "address_prefixes" {
  value = jsonencode(module.base.address_prefixes)
}

output "workspace_vm_allowed_fqdns_list" {
  value = jsonencode(local.workspace_vm_allowed_fqdns_list)
}
