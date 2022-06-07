locals {
  location             = data.azurerm_resource_group.rg.location
  dbfsBlobStrageDomain = [replace("<stgacc>.blob.core.windows.net", "<stgacc>", azurerm_databricks_workspace.databricks.custom_parameters[0].storage_account_name)]
}

resource "azurerm_firewall_network_rule_collection" "networkrulecollection" {
  name                = "nrc-${local.workspace_resource_name_suffix}"
  azure_firewall_name = data.azurerm_firewall.firewall.name
  resource_group_name = data.azurerm_firewall.firewall.resource_group_name
  priority            = 10100
  action              = "Allow"

  rule {
    name             = "databricks-webapp"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    destination_ports = [
      "80",
      "443"
    ]
    destination_addresses = local.mapLocationUrlConfig[local.location].webappDestinationAddresses
    protocols = [
      "TCP"
    ]
    description = "Communication with Azure Databricks webapp."
  }

  rule {
    name             = "databricks-extended-infrastructure-ip"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    destination_ports = [
      "80",
      "443"
    ]
    destination_addresses = local.mapLocationUrlConfig[local.location].extendedInfrastructureDestinationAddresses
    protocols = [
      "TCP"
    ]
    description = "Databricks extended infrastucture IP."
  }

  rule {
    name             = "databricks-sql-metastore"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    destination_ports = [
      "3306"
    ]
    destination_fqdns = local.mapLocationUrlConfig[local.location].metastoreDomains
    protocols = [
      "TCP"
    ]
    description = "Stores metadata for databases and child objects in a Azure Databricks workspace."
  }

  rule {
    name             = "databricks-observability-eventhub"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    destination_ports = [
      "9093"
    ]
    destination_fqdns = local.mapLocationUrlConfig[local.location].eventHubEndpointDomains
    protocols = [
      "TCP"
    ]
    description = "Transit for Azure Databricks on-cluster service specific telemetry."
  }
}

resource "azurerm_firewall_application_rule_collection" "apprulecollection" {
  name                = "arc-${local.workspace_resource_name_suffix}"
  azure_firewall_name = data.azurerm_firewall.firewall.name
  resource_group_name = data.azurerm_firewall.firewall.resource_group_name
  priority            = 20100
  action              = "Allow"

  rule {
    name             = "databricks-spark-log-blob-storage"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    target_fqdns     = local.mapLocationUrlConfig[local.location].logBlobstorageDomains
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
    description = "To store Azure Databricks audit and cluster logs (anonymized / masked) for support and troubleshooting."
  }

  rule {
    name             = "databricks-artifact-blob-storage"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    target_fqdns     = concat(local.mapLocationUrlConfig[local.location].artifactBlobStoragePrimaryDomains, local.mapLocationUrlConfig[local.location].artifactBlobStorageSecondaryDomains)
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
    description = "Stores Databricks Runtime images to be deployed on cluster nodes."
  }

  rule {
    name             = "databricks-dbfs"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    target_fqdns     = local.dbfsBlobStrageDomain
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
    description = "Azure Databricks workspace root storage."
  }

  rule {
    name             = "databricks-public-repo"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    target_fqdns = [
      "*.pypi.org",
      "cdnjs.com",
      "cdnjs.cloudflare.com"
    ]
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
    description = "Public Repositories for Python and R Libraries. 'cdnjs' is used by Ganglia UI."
  }

  rule {
    name             = "databricks-scc-relay"
    source_addresses = concat(azurerm_subnet.public.address_prefixes, azurerm_subnet.private.address_prefixes)
    target_fqdns     = local.mapLocationUrlConfig[local.location].sccRelayDomains
    protocol {
      port = "443"
      type = "Https"
    }
    protocol {
      port = "80"
      type = "Http"
    }
    description = "Databricks SCC Relay IP."
  }

  depends_on = [
    azurerm_firewall_network_rule_collection.networkrulecollection
  ]
}
