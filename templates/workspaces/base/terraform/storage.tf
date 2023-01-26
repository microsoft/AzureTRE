resource "azurerm_storage_account" "stg" {
  name                     = local.storage_name
  resource_group_name      = azurerm_resource_group.ws.name
  location                 = azurerm_resource_group.ws.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  is_hns_enabled           = true
  tags                     = local.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_share" "shared_storage" {
  name                 = "vm-shared-storage"
  storage_account_name = azurerm_storage_account.stg.name
  quota                = var.shared_storage_quota

  depends_on = [
    azurerm_private_endpoint.stgfilepe,
    azurerm_storage_account_network_rules.stgrules
  ]
}

resource "azurerm_storage_container" "stgcontainer" {
  name                  = "datalake"
  storage_account_name  = azurerm_storage_account.stg.name
  container_access_type = "private"
}

resource "azurerm_storage_account_network_rules" "stgrules" {
  storage_account_id = azurerm_storage_account.stg.id

  # When deploying from a local machine we need to "allow"
  default_action = var.enable_local_debugging ? "Allow" : "Deny"
  bypass         = ["AzureServices"]
}

resource "azurerm_private_endpoint" "stgfilepe" {
  name                = "stgfilepe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network,
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.filecore_zone_id]
  }

  private_service_connection {
    name                           = "stgfilepesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["File"]
  }
}

resource "azurerm_private_endpoint" "stgblobpe" {
  name                = "stgblobpe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network,
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.blobcore_zone_id]
  }

  private_service_connection {
    name                           = "stgblobpesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

resource "azurerm_private_endpoint" "stgdfspe" {
  name                = "stgdfspe-${local.workspace_resource_name_suffix}"
  location            = azurerm_resource_group.ws.location
  resource_group_name = azurerm_resource_group.ws.name
  subnet_id           = module.network.services_subnet_id
  tags                = local.tre_workspace_tags

  depends_on = [
    module.network,
  ]

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [module.network.dfscore_zone_id]
  }

  private_service_connection {
    name                           = "stgdfspesc-${local.workspace_resource_name_suffix}"
    private_connection_resource_id = azurerm_storage_account.stg.id
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }
}
