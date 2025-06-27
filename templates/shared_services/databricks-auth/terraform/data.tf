data "azurerm_resource_group" "rg" {
  name = local.core_resource_group_name
}

data "azurerm_virtual_network" "core" {
  name                = local.core_virtual_network_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_subnet" "services" {
  name                 = "SharedSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_virtual_network.core.resource_group_name
}

data "azurerm_private_dns_zone" "databricks" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azuredatabricks.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "dfscore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.dfs.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_resource_group" "databricks_managed_resource_group" {
  name = split("/", azurerm_databricks_workspace.databricks.managed_resource_group_id)[4]

  depends_on = [azurerm_databricks_workspace.databricks]
}

data "azurerm_resources" "databricks_managed_resource_list" {
  resource_group_name = data.azurerm_resource_group.databricks_managed_resource_group.name
  type                = "Microsoft.Storage/storageAccounts"
}

data "azurerm_storage_account" "databricks_managed_storage_account" {
  name                = data.azurerm_resources.databricks_managed_resource_list.resources[0].name
  resource_group_name = data.azurerm_resources.databricks_managed_resource_list.resource_group_name
}

data "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}
