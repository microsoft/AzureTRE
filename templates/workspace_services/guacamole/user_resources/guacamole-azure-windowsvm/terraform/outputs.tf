output "ip" {
  value = module.windows_vm.ip
}

output "hostname" {
  value = module.windows_vm.hostname
}

output "azure_resource_id" {
  value = module.windows_vm.azure_resource_id
}

output "connection_uri" {
  value = module.windows_vm.connection_uri
}

output "vm_username" {
  value = module.windows_vm.vm_username
}

output "vm_password_secret_name" {
  value = module.windows_vm.vm_password_secret_name
}

output "keyvault_name" {
  value = module.windows_vm.keyvault_name
}
