resource "azurerm_virtual_network" "ws" {
  name                = local.virtual_network_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = local.resource_group_name
  address_space       = local.address_space
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_subnet" "host" {
  name                 = local.host_subnet_name
  resource_group_name  = local.resource_group_name
  virtual_network_name = azurerm_virtual_network.ws.name
  address_prefixes     = [local.host_subnet_address_space]

  delegation {
    name = "db-host-vnet-integration"

    service_delegation {
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
      name = "Microsoft.Databricks/workspaces"
    }
  }
}

resource "azurerm_subnet" "container" {
  name                 = local.container_subnet_name
  resource_group_name  = local.resource_group_name
  virtual_network_name = azurerm_virtual_network.ws.name
  address_prefixes     = [local.container_subnet_address_space]

  delegation {
    name = "db-container-vnet-integration"

    service_delegation {
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
      name = "Microsoft.Databricks/workspaces"
    }
  }
}

resource "azurerm_network_security_group" "nsg" {
  name                = local.network_security_group_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = local.resource_group_name

  tags = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }

  security_rule {
    name                       = "AllowInboundDatabricksWorkerNodesToCluster"
    description                = "Required for worker nodes communication within a cluster."
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "AllowOutboundDatabricksWorkerNodesToControlPlain"
    description                = "Required for workers communication with Databricks Webapp."
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "AzureDatabricks"
  }

  security_rule {
    name                       = "AllowOutboundDatabricksWorkerNodesToAzureSQLServices"
    description                = "Required for workers communication with Azure SQL services."
    priority                   = 101
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3306"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "Sql"
  }

  security_rule {
    name                       = "AllowOutboundDatabricksWorkerNodesToAzureStorage"
    description                = "Required for workers communication with Azure Storage services."
    priority                   = 102
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "Storage"
  }

  security_rule {
    name                       = "AllowOutboundDatabricksWorkerNodesWithinACluster"
    description                = "Required for worker nodes communication within a cluster."
    priority                   = 103
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  security_rule {
    name                       = "AllowOutboundWorkerNodesToAzureEventhub"
    description                = "Required for worker communication with Azure Eventhub services."
    priority                   = 104
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "9093"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "EventHub"
  }
}

resource "azurerm_subnet_network_security_group_association" "container" {
  subnet_id                 = azurerm_subnet.container.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_subnet_network_security_group_association" "host" {
  subnet_id                 = azurerm_subnet.host.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}


resource "azurerm_private_endpoint" "databricks_auth_private_endpoint" {
  name                = "pe-adb-auth-${local.service_resource_name_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = local.resource_group_name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    name                           = "private-service-connection-databricks-auth-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_databricks_workspace.databricks.id
    is_manual_connection           = false
    subresource_names              = ["browser_authentication"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-databricks-auth-${local.service_resource_name_suffix}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.databricks.id]
  }
}

resource "azurerm_private_endpoint" "databricks_filesystem_private_endpoint" {
  name                = "pe-adb-fs-${local.service_resource_name_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    name                           = "private-service-connection-databricks-filesystem-${local.service_resource_name_suffix}"
    private_connection_resource_id = join("", [azurerm_databricks_workspace.databricks.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${data.azurerm_storage_account.databricks_managed_storage_account.name}"])
    is_manual_connection           = false
    subresource_names              = ["dfs"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-databricks-filesystem-${local.service_resource_name_suffix}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.dfscore.id]
  }

  depends_on = [
    data.azurerm_storage_account.databricks_managed_storage_account
  ]
}

resource "azurerm_private_endpoint" "databricks_blob_private_endpoint" {
  name                = "pe-adb-blob-${local.service_resource_name_suffix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.tre_shared_service_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    name                           = "private-service-connection-databricks-blob-${local.service_resource_name_suffix}"
    private_connection_resource_id = join("", [azurerm_databricks_workspace.databricks.managed_resource_group_id, "/providers/Microsoft.Storage/storageAccounts/${data.azurerm_storage_account.databricks_managed_storage_account.name}"])
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-databricks-blob-${local.service_resource_name_suffix}"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  depends_on = [
    data.azurerm_storage_account.databricks_managed_storage_account
  ]
}
