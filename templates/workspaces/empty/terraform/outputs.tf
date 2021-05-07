output "name" {
  value = var.name
}

output "workspace_id" {
  value = var.workspace_id
}

output "address_space" {
  value = azurerm_virtual_network.workspace.address_space[0]
}

