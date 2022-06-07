output "host_subnet_name" {
  value = azurerm_subnet.public.name
}

output "container_subnet_name" {
  value = azurerm_subnet.private.name
}

output "databricks_workspace_name" {
  value = azurerm_databricks_workspace.databricks.name
}

output "databricks_workspace_url" {
  value = azurerm_databricks_workspace.databricks.workspace_url
}

output "databricks_storage_account_name" {
  value = azurerm_databricks_workspace.databricks.custom_parameters[0].storage_account_name
}

output "firewall-public-ip-address" {
  value = data.azurerm_public_ip.firewall-public-ip.ip_address
}
